"""
generate the verilog with
$ python3 multleave.py
"""
from nmigen import Elaboratable, Signal, Module
from nmigen import signed

from maeri.customize.mult import Mult
from maeri.compiler.assembler.states import InjectEn
from maeri.gateware.compute_unit.config_bus import ConfigBus
from maeri.common.helpers import print_sig

class MultNode(Elaboratable):
    def __init__(self, ID, INPUT_WIDTH=8):
        self.INPUT_WIDTH = INPUT_WIDTH
        self.ID = ID

        # inputs
        self.Inject_in = Signal(INPUT_WIDTH)
        self.F_in = Signal(INPUT_WIDTH)
        self.Config_Bus_top_in = ConfigBus(f"config_in_node_{ID}", INPUT_WIDTH)

        # outputs
        self.F_out = Signal(INPUT_WIDTH)
        # holds the product
        self.Up_out = Signal(signed(INPUT_WIDTH))

        # submodules
        self.mult = Mult(INPUT_WIDTH=INPUT_WIDTH)

        # expose some internals
        self.state = Signal(InjectEn)

    def elaborate(self,platform):
        m = Module()

        # internals
        inject_en = self.state
        weight = self.weight = Signal(signed(self.INPUT_WIDTH))
        feature = self.feature = Signal(signed(self.INPUT_WIDTH))
        self.id = Signal(8)

        # set internal ID
        m.d.comb += self.id.eq(self.ID)

        # select value to be forwarded on whether
        # or not we are in injection mode
        # select whether feature is set to injected
        # value or forwarded in value
        with m.If(inject_en):
            m.d.comb += feature.eq(self.Inject_in)
            m.d.sync += self.F_out.eq(self.Inject_in)
        with m.Else():
            m.d.comb += feature.eq(self.F_in)
            m.d.sync += self.F_out.eq(self.F_in)

        # attach and wire up multiplies submodule
        m.submodules.mult = self.mult
        m.d.comb += [
            self.mult.A_in.eq(feature),
            self.mult.B_in.eq(weight),
        ]

        m.d.sync += self.Up_out.eq(
            self.mult.Product_out[(self.INPUT_WIDTH- 1): -1]
            )

        # update the weights from values on the config
        # bus when we are in configuration mode
        # also update mult state to state on config bus
        # when in config mode
        with m.If(self.Config_Bus_top_in.en):
            with m.If(self.Config_Bus_top_in.addr == self.id):
                with m.If(self.Config_Bus_top_in.set_weight):
                        m.d.sync += weight.eq(self.Config_Bus_top_in.data)
                with m.Else():
                    with m.If(self.Config_Bus_top_in.addr == self.id):
                        m.d.sync += inject_en.eq(self.Config_Bus_top_in.data[0])
        
        return m

    def print_state(self):
        # to use in simulation, do
        # yield from multnode.print_state()
        print(f"mult_node[{yield self.id}] : ", end='')
        yield from print_sig(self.weight, newline=False)
        yield from print_sig(self.feature, newline=False)
        yield from print_sig(self.inject_en, newline=True)

    def ports(self):
        ports = []
        ports += self.Inject_in, self.F_in
        ports += [self.Config_Bus_top_in[sig] 
            for sig in self.Config_Bus_top_in.fields]
        ports += self.F_out, self.Up_out
        return ports

from nmigen.cli import main
if __name__ == "__main__":
    top = MultNode(ID=1, INPUT_WIDTH=8)

    # generate verilog
    from nmigen.back import verilog
    name = __file__[:-3]
    f = open(f"{name}.v", "w")
    f.write(verilog.convert(top, 
        name = name,
        strip_internal_attrs=True,
        ports=top.ports()
        ))