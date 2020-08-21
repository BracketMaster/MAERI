"""
generate some smoketest verilog with:
$ python3 adder.py
"""

from nmigen import Elaboratable, Signal, Module
from nmigen import signed

class Adder3(Elaboratable):
    def __init__(self, INPUT_WIDTH):
        self.PARAMS = {"INPUT_WIDTH":INPUT_WIDTH}

        # inputs
        self.A_in = Signal(signed(INPUT_WIDTH))
        self.B_in = Signal(signed(INPUT_WIDTH))
        self.C_in = Signal(signed(INPUT_WIDTH))

        # outputs
        self.C_out = Signal(signed(INPUT_WIDTH))
    
    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.C_out.eq(
            self.A_in + self.B_in + self.C_in
        )
        return m
    
    def ports(self):
        return [self.A_in,
                self.B_in,
                self.C_in,
                self.C_out]

from nmigen.cli import main
if __name__ == "__main__":
    top = Adder3(INPUT_WIDTH=8)

    # generate verilog
    from nmigen.back import verilog
    name = __file__[:-3]
    f = open(f"{name}.v", "w")
    f.write(verilog.convert(top, 
        name = name,
        strip_internal_attrs=True,
        ports=top.ports()
        ))