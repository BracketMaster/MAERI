from nmigen import Signal, Elaboratable, Module
from nmigen import signed

from maeri.common.skeleton import Skeleton
from maeri.gateware.compute_unit.config_bus import ConfigBus
from maeri.gateware.compute_unit.adder_node import AdderNode
from maeri.gateware.compute_unit.mult_node import MultNode

class ReductionNetwork(Elaboratable):
    def __init__(self, depth, num_ports, INPUT_WIDTH, 
            bytes_in_line, VERBOSE = False):
        """
        Attributes:
        ===========
        self.skel_v_hw_dict:
        self.mults:
        self.adders:
        self.skeleton:
        inputs:
        self.select_ports:
        self.config_ports_in:
        self.inject_ports:

        outputs:
        self.collect_ports:

        """

        # common parameters
        self.num_ports = num_ports
        self.INPUT_WIDTH = INPUT_WIDTH

        # skeleton on top of which maeri will be created
        self.skeleton = Skeleton(depth, num_ports, bytes_in_line=bytes_in_line, VERBOSE=VERBOSE)

        # create list of selection ports
        self.select_ports = []
        for port in range(num_ports):
            self.select_ports.append(
                Signal(signed(INPUT_WIDTH), 
                    name=f"select_port_{port}"))

        # create list of collection ports
        self.collect_ports = []
        for port in range(num_ports):
            self.collect_ports.append(
                Signal(signed(INPUT_WIDTH), 
                    name=f"collect_port_{port}"))

        # create list of config ports
        self.config_ports_in = []
        for port in range(bytes_in_line):
            self.config_ports_in.append(ConfigBus(
                name = f"maeri_config_port_{port}",
                INPUT_WIDTH = INPUT_WIDTH))
        

        # create list of injection ports
        self.inject_ports = []
        for port in range(num_ports):
            self.inject_ports.append(
                Signal(signed(INPUT_WIDTH), 
                    name=f"inject_port_{port}"))

    def elaborate(self, platform):
        m = Module()

        # instantiate adder_nodes in tree
        self.adders = adders = []
        for node in self.skeleton.adder_nodes:
            # generate adder instance
            submod = AdderNode(node.id, self.INPUT_WIDTH)
            
            # add generated adder as named submodule
            setattr(m.submodules, f"adder_node{node.id}", submod)
            
            # pop onto adders list for easy access
            adders += [submod]

        # instantiate mult_nodes in tree
        self.mults = mults = []
        for node in self.skeleton.mult_nodes:
            # generate adder instance
            submod = MultNode(node.id, self.INPUT_WIDTH)
            
            # add generated adder as named submodule
            setattr(
                m.submodules, f"mult_node{node.id}", submod
                )
            
            # pop onto adders list for easy access
            mults += [submod]
        
        # combine adders and mults into one list
        all_nodes_hw = adders + mults
        self.skel_v_hw_dict = {}
        hw_skel_pairs = zip(self.skeleton.all_nodes, all_nodes_hw)
        for skel_node, maeri_node in hw_skel_pairs:
            self.skel_v_hw_dict[skel_node] = maeri_node

        # sanity check
        for node in self.skel_v_hw_dict:
            skel_node = node
            maeri_node = self.skel_v_hw_dict[skel_node]
            assert(maeri_node.ID == skel_node.id)
        
        # connect injection ports to injection nodes
        assert(len(self.inject_ports) == len(self.skeleton.inject_nodes))
        port_inject_pairs = zip(self.inject_ports, self.skeleton.inject_nodes)
        for port, skel_node in port_inject_pairs:
            inject_node_hw = self.skel_v_hw_dict[skel_node]
            m.d.comb += inject_node_hw.Inject_in.eq(port)

        # connect config ports of each respective node
        # to one of the external config ports
        port_node_pairs = zip(self.config_ports_in, self.skeleton.config_groups)
        for config_port, config_group in port_node_pairs:
            for node in config_group:
                node = self.skel_v_hw_dict[node]
                m.d.comb += node.Config_Bus_top_in.connect(config_port)

        # connect left and right sum links from children
        # to parent adder nodes
        for node in self.skeleton.all_nodes:
            if self.has_children(node):
                self.connect_children_sum_links(m, node)
        
        # allow collection port to select which node
        # it collects from        
        assert(len(self.select_ports) == len(self.collect_ports))
        for sel_port, coll_port in zip(self.select_ports, self.collect_ports):
            with m.Switch(sel_port):
                for skel_node in self.skeleton.adder_nodes:
                    maeri_node = self.skel_v_hw_dict[skel_node]
                    with m.Case(skel_node.id):
                        m.d.comb += coll_port.eq(maeri_node.Up_out)
                with m.Default():
                    m.d.comb += coll_port.eq(0)
        
        # link up forwarding links between adders
        for left, right in self.skeleton.adder_forwarding_links:
            left_hw = self.skel_v_hw_dict[left]
            right_hw = self.skel_v_hw_dict[right]
            # adder forwarding links are  bidirectional
            m.d.comb += left_hw.F_in.eq(right_hw.F_out)
            m.d.comb += right_hw.F_in.eq(left_hw.F_out)

        # link up forwarding links between mults
        for left, right in self.skeleton.mult_forwarding_links:
            left_hw = self.skel_v_hw_dict[left]
            right_hw = self.skel_v_hw_dict[right]
            m.d.comb += left_hw.F_in.eq(right_hw.F_out)

        return m
    
    def connect_children_sum_links(self, m, skel_node):
        parent_node_hw = self.skel_v_hw_dict[skel_node]
        lhs_node_hw = self.skel_v_hw_dict[skel_node.lhs]
        rhs_node_hw = self.skel_v_hw_dict[skel_node.rhs]

        m.d.comb += parent_node_hw.lhs_in.eq(lhs_node_hw.Up_out)
        m.d.comb += parent_node_hw.rhs_in.eq(rhs_node_hw.Up_out)

    def has_children(self, skel_node):
        if skel_node.lhs and skel_node.rhs:
            return True
        return False

    def ports(self):
        ports = []
        ports += self.select_ports
        ports += self.collect_ports
        ports += self.inject_ports
        for port in self.config_ports_in:
            ports += [port[sig] for sig in port.fields]
        
        return ports

if __name__ == "__main__":
    top = ReductionNetwork(depth = 5, num_ports = 4, INPUT_WIDTH = 8, 
            bytes_in_line = 4, VERBOSE=True)

    # generate verilog
    from nmigen.back import verilog
    name = __file__[:-3]
    f = open(f"{name}.v", "w")
    f.write(verilog.convert(top, 
        name = name,
        strip_internal_attrs=True,
        ports=top.ports())
    )
