"""
generate some smoketest verilog with:
$ python3 addernode.py
"""
from collections import defaultdict
from nmigen import Elaboratable, Signal, Module
from nmigen import signed

from maeri.compiler.ISA.states import ConfigUp, ConfigForward
from maeri.customize.adder import Adder3
from maeri.gateware.compute_unit.config_bus import ConfigBus

class AdderNode(Elaboratable):
    def __init__(self,ID, INPUT_WIDTH=8):
        """
        Implements an adder node that follows the
        state table described in `maeri.common.enums`.

        The adder node can be configured from the top
        config in bus, and duplicates config on next
        cycle to the top bus of its two children.
        """
        self.INPUT_WIDTH = INPUT_WIDTH
        self.ID = ID

        # inputs
        self.lhs_in = Signal(signed(INPUT_WIDTH))
        self.rhs_in = Signal(signed(INPUT_WIDTH))
        self.F_in = Signal(signed(INPUT_WIDTH))
        self.Config_Bus_top_in = ConfigBus(f"config_in_node_{ID}", INPUT_WIDTH)


        # outputs
        self.Up_out = Signal(signed(INPUT_WIDTH))
        self.F_out = Signal(signed(INPUT_WIDTH))
        
        # submodules
        self.adder = Adder3(INPUT_WIDTH=INPUT_WIDTH)

        # lookup table(dict) for adder_node state
        self.up_dict = up_dict = defaultdict(lambda : 'ZERO')
        self.f_dict = f_dict = defaultdict(lambda : 'ZERO')
        [up_dict.update({conf.value:conf.name}) for conf in ConfigUp]
        [f_dict.update({conf.value:conf.name}) for conf in ConfigForward]

    
    def elaborate(self, platform):
        m = Module()
        
        # internals
        # the adder node can have 5 states
        self.state = Signal(ConfigUp)
        self.id_reg = Signal(8)
        adder_sum = Signal(self.INPUT_WIDTH * 2)

        # set the ID
        m.d.comb += self.id_reg.eq(self.ID)

        # configuration
        # change the adder state to the state on 
        # config bus when in config mode
        with m.If(self.Config_Bus_top_in.en):
            with m.If(~self.Config_Bus_top_in.set_weight):
                with m.If(self.Config_Bus_top_in.addr == self.id_reg):
                    # the state is pulled from the lower
                    # bits of the data bus
                    m.d.sync += self.state.eq(
                        self.Config_Bus_top_in.data[:self.state.width])

        # attach adder as submodule
        m.submodules.adder = self.adder
        m.d.comb += self.adder.A_in.eq(self.lhs_in)
        m.d.comb += self.adder.B_in.eq(self.rhs_in)
        m.d.comb += adder_sum.eq(self.adder.C_out)

        # the three input adder only uses the
        # forward_in link in state 2
        with m.If(self.state == 2):
            m.d.comb += self.adder.C_in.eq(self.F_in)
        with m.Else():
            m.d.comb += self.adder.C_in.eq(0)
        
        # truth table on forward out
        with m.Switch(self.state):
            with m.Case(ConfigForward.sum_l_r):
                m.d.comb += self.F_out.eq(adder_sum)
            with m.Case(ConfigForward.r):
                m.d.comb += self.F_out.eq(self.rhs_in)
            with m.Case(ConfigForward.l):
                m.d.comb += self.F_out.eq(self.lhs_in)
            with m.Default():
                m.d.comb += self.F_out.eq(0)

        # truth table on up out
        with m.Switch(self.state):
            with m.Case(ConfigUp.sum_l_r):
                m.d.sync += self.Up_out.eq(adder_sum)
            with m.Case(ConfigUp.sum_l_r_f):
                m.d.sync += self.Up_out.eq(adder_sum)
            with m.Case(ConfigUp.l):
                m.d.sync += self.Up_out.eq(self.lhs_in)
            with m.Case(ConfigUp.r):
                m.d.sync += self.Up_out.eq(self.rhs_in)
            with m.Default():
                m.d.sync += self.Up_out.eq(0)
            
        return m
    
    def print_state(self):
        # to use in simulation, do
        # yield from addernode.print_state()

        adder_state = (yield self.state)
        up_state = self.up_dict[adder_state]
        forward_state = self.f_dict[adder_state]

        print(
            f"adder_node[{yield self.id_reg}].up" + 
            f" = {up_state} = {(yield self.Up_out)}"
            )
        print(
            f"adder_node[{yield self.id_reg}].forward" + 
            f" = {forward_state} = {(yield self.F_out)}"
            )

    def ports(self):
        ports = []
        ports += self.lhs_in, self.rhs_in, self.F_in
        ports += self.Up_out, self.F_out
        ports += [self.Config_Bus_top_in[sig] 
            for sig in self.Config_Bus_top_in.fields]
        return ports

if __name__ == "__main__":
    top = AdderNode(ID=1, INPUT_WIDTH=8)

    # generate verilog
    from nmigen.back import verilog
    name = __file__[:-3]
    f = open(f"{name}.v", "w")
    f.write(verilog.convert(top, 
        name = name,
        strip_internal_attrs=True,
        ports=top.ports()
        ))