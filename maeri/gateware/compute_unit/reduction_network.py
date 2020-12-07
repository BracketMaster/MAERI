from nmigen import Signal, Elaboratable, Module
from nmigen import Array, signed

from maeri.common.skeleton import Skeleton
from maeri.gateware.compute_unit.config_bus import ConfigBus
from maeri.gateware.compute_unit.adder_node import AdderNode
from maeri.gateware.compute_unit.mult_node import MultNode
from maeri.gateware.compute_unit.sram_w32_r8 import Sram_w32_r8
from maeri.gateware.compute_unit.sram_w8_r32 import Sram_w8_r32
from nmigen import Memory

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
        self.select_output_node_ports:
        self.config_bus_ports:
        self.sel_sram:
        self.w_sram_data:
        self.w_sram_en:
        self.r_sram_en:
        self.run:
        self.length:
        self.relu_en_by_port:
        
        outputs:
        self.r_sram_data
        self.done

        Formal
        ======
        Externally, the injection srams can only be written
        to and the collection srams can only be read from.
        Must make sure that interally, injection srams are
        not being written to externally while being read from
        internally.
        """

        # common parameters
        self.num_ports = num_ports
        self.INPUT_WIDTH = INPUT_WIDTH


        # skeleton on top of which maeri will be created
        self.skeleton = \
            Skeleton(depth, num_ports, bytes_in_line=bytes_in_line, VERBOSE=VERBOSE)
        
        # control parameters -- inputs
        self.sel_sram = Signal(range(num_ports))
        self.w_sram_data = Signal(signed(INPUT_WIDTH))
        self.w_sram_en = Signal()
        self.r_sram_en = Signal()
        # moves data from injection FIFOs over the
        # reduction network to the collection FIFOs
        self.run = Signal()
        self.length = Signal(6)
        self.relu_en_by_port = [Signal() for port in range(num_ports)]
        self.done = Signal()

        # control parameters -- outputs
        self.r_sram_data = Signal(signed(INPUT_WIDTH))
        
        # make list of injection srams
        self.injection_srams = []
        for port in range(num_ports):
            self.injection_srams.append(Sram_w32_r8())
        # make list of collection srams
        self.collection_srams = []
        for port in range(num_ports):
            self.collection_srams.append(Sram_w8_r32())

        # create list of selection ports
        # allows to select which nodes the 
        # collect fifos listen to
        self.select_output_node_ports = []
        for port in range(num_ports):
            self.select_output_node_ports.append(
                Signal(INPUT_WIDTH, 
                    name=f"select_port_{port}"))

        # create list of config ports
        self.config_bus_ports = []
        for port in range(bytes_in_line):
            self.config_bus_ports.append(ConfigBus(
                name = f"maeri_config_port_{port}",
                INPUT_WIDTH = INPUT_WIDTH))
        
        # instantiate adder_nodes in tree
        self.adders = adders = []
        for node in self.skeleton.adder_nodes:
            # generate and append adder instance
            adders += [AdderNode(node.id, LATENCY=node.latency,INPUT_WIDTH=INPUT_WIDTH)]
            
        # instantiate mult_nodes in tree
        self.mults = mults = []
        for node in self.skeleton.mult_nodes:
            # generate and append mult instance
            mults += [MultNode(node.id, LATENCY=node.latency,INPUT_WIDTH=INPUT_WIDTH)]

    def elaborate(self, platform):
        m = Module()

        adders = self.adders
        mults = self.mults

        for node in adders:
            # add generated adder as named submodule
            setattr(m.submodules, f"adder_node{node.ID}", node)
        
        # register injection srams as submodules
        for ID, sram in enumerate(self.injection_srams):
            setattr(m.submodules, f"injection_sram_{ID}", sram)

        # register collection srams as submodules
        for ID, sram in enumerate(self.collection_srams):
            setattr(m.submodules, f"collection_sram_{ID}", sram)
        
        # each collect port has a done signal
        done_by_collect_port = Array([Signal() for port in range(self.num_ports)])
        injection_addr = Signal.like(self.length)
        injection_finished = Signal()
        
        # build multiplexer for  selection of particular 
        # injection fifo
        wp_en_by_injection_sram = Array([sram.wp_en for sram in self.injection_srams])
        wp_data_by_injection_sram = Array([sram.wp_data for sram in self.injection_srams])
        m.d.comb += wp_en_by_injection_sram[self.sel_sram].eq(self.w_sram_en)
        m.d.comb += wp_data_by_injection_sram[self.sel_sram].eq(self.w_sram_data)

        # inject data into reduction tree
        m.d.comb += [sram.rp_addr.eq(injection_addr) for sram in self.injection_srams]
        with m.If(self.run):
            increment_condition_1 = self.run
            increment_condition_2 = injection_addr < (self.length - 1)
            with m.If(increment_condition_1 & increment_condition_2):
                m.d.comb += [sram.rp_en.eq(1) for sram in self.injection_srams]
                m.d.sync += injection_addr.eq(injection_addr + 1)
            with m.Elif(increment_condition_1):
                m.d.sync += injection_addr.eq(injection_addr)
            with m.Else():
                m.d.sync += injection_addr.eq(0)
        
        # collect data from reduction tree
        latency_by_node = Array([node.latency for node in (adders + mults)])
        addr_by_collector = [Signal.like(self.length) for collector in range(self.num_ports)]
        assert(len(addr_by_collector) == len(self.collection_srams))
        zipped_list =  zip(self.collection_srams, addr_by_collector, self.select_output_node_ports)
        for sram, collector_addr, selected_port in zipped_list:
            m.d.comb += sram.wp_addr.eq(collector_addr)
            increment_condition_1 = self.run
            increment_condition_2 = injection_addr > latency_by_node[selected_port]
            increment_condition_3 = collector_addr < (self.length - 1)
            with m.If(increment_condition_1 & increment_condition_2 & increment_condition_3):
                m.d.sync += collector_addr.eq(collector_addr + 1)
                m.d.comb += sram.wp_en.eq(1)
            with m.Elif(increment_condition_1):
                # TODO : test if "pass" works
                m.d.sync += collector_addr.eq(collector_addr)
            with m.Else():
                m.d.sync += collector_addr.eq(0)

        # earlier, we expose once read port width-matched to main
        # memory width, namely, self.r_sram_data
        # below is the logic for choosing which internal sram self.r_sram_data
        # is connected to
        rp_en_by_collection_sram = Array([sram.rp_en for sram in self.collection_srams])
        rp_data_by_collection_sram = Array([sram.rp_data for sram in self.collection_srams])
        m.d.comb += rp_en_by_collection_sram[self.sel_sram].eq(self.r_sram_en)
        m.d.comb += self.r_sram_data.eq(rp_data_by_collection_sram[self.sel_sram])

        for node in mults:
            # add generated adder as named submodule
            setattr(m.submodules, f"mult_node{node.ID}", node)
        
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
        assert(len(self.injection_srams) == len(self.skeleton.inject_nodes))
        sram_inject_pairs = zip(self.injection_srams, self.skeleton.inject_nodes)
        for sram, skel_node in sram_inject_pairs:
            inject_node_hw = self.skel_v_hw_dict[skel_node]
            m.d.comb += inject_node_hw.Inject_in.eq(sram.rp_data)

        # connect config ports of each respective node
        # to one of the external config ports
        port_node_pairs = zip(self.config_bus_ports, self.skeleton.config_groups)
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
        assert(len(self.select_output_node_ports) == len(self.collection_srams))
        for sel_port, sram in zip(self.select_output_node_ports, self.collection_srams):
            with m.Switch(sel_port):
                for skel_node in self.skeleton.adder_nodes:
                    maeri_node = self.skel_v_hw_dict[skel_node]
                    with m.Case(skel_node.id):
                        m.d.comb += sram.wp_data.eq(maeri_node.Up_out)
                with m.Default():
                    m.d.comb += sram.wp_data.eq(0)
        
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

        # inputs
        ports += self.select_output_node_ports
        for port in self.config_bus_ports:
            ports += [port[sig] for sig in port.fields]
        ports += [self.sel_sram]
        ports += [self.w_sram_data]
        ports += [self.w_sram_en]
        ports += [self.r_sram_en]
        ports += [self.run]
        ports += [self.length]
        ports += self.relu_en_by_port

        # outputs
        ports += [self.r_sram_data]
        ports += [self.done]
        
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
