"""
generate the verilog with:
$ python3 mult.py generate > mult.v
"""

from nmigen import Elaboratable, Signal, Module, Cat
from nmigen import signed

class Mult(Elaboratable):
    def __init__(self, INPUT_WIDTH):
        self.PARAMS = {"INPUT_WIDTH":INPUT_WIDTH}

        # inputs
        self.A_in = Signal(signed(INPUT_WIDTH))
        self.B_in = Signal(signed(INPUT_WIDTH))

        # outputs
        self.Product_out = Signal(signed(INPUT_WIDTH*2))

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.Product_out.eq(
            self.A_in*self.B_in
        )
        return m
    
    def ports(self):
        return [self.A_in, self.B_in, self.Product_out]

from nmigen.cli import main
if __name__ == "__main__":
    top = Mult(INPUT_WIDTH=8)
    main(top, ports=top.ports())