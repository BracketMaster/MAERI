"""
formal verification of adder.
A.K.A, we mathematically prove the adder 
works.

We assume a 16 bit adder.
"""
from nmigen import (Module, Signal, Elaboratable, Mux, Cat, Repl,
                    signed)
from nmigen.asserts import Assert, AnyConst, Assume, Cover
from maeri.gateware.formal import FHDLTestCase
from maeri.customize.adder import Adder3
import unittest

TEST_WIDTH = 16

class Driver(Elaboratable):
    def __init__(self):
        # no additional signals needed
        pass

    def elaborate(self, platform):
        m = Module()
        m.submodules.adder3 = adder = Adder3(INPUT_WIDTH=TEST_WIDTH)

        m.d.comb += [
            adder.A_in.eq(AnyConst(TEST_WIDTH)),
            adder.B_in.eq(AnyConst(TEST_WIDTH)),
            adder.C_in.eq(AnyConst(TEST_WIDTH))
            ]

        result = Signal(signed(TEST_WIDTH))
        m.d.comb += result.eq(adder.A_in + adder.B_in + adder.C_in)
        m.d.comb += Assert(adder.C_out == result
            )

        return m

class TestAdder3(FHDLTestCase):

    def test_formal(self):
        module = Driver()
        self.assertFormal(module, mode="bmc", depth=2)
        self.assertFormal(module, mode="cover", depth=2)


if __name__ == "__main__":
    unittest.main()
