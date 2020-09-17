"""
Formal verification of adder node.
"""
from nmigen import (Module, Signal, Elaboratable, Mux, Cat, Repl,
                    signed, ResetSignal)
from nmigen.asserts import (Assert, AnyConst, Assume, Cover, Initial,
                    Rose, Fell, Stable, Past, AnySeq)

from maeri.common.enums import ConfigUp, ConfigForward
from maeri.gateware.formal import FHDLTestCase
from maeri.gateware.core.adder_node import AdderNode

import unittest

TEST_WIDTH = 8

class Driver(AdderNode):
    """
    Formal isn't super useful here beyond checking 
    that I can write RTL. It is more robust than
    a testbench though.

    Typically formal is more useful during rule and
    violation checks.
    """
    def __init__(self):
        super().__init__(ID=1, INPUT_WIDTH=TEST_WIDTH)

    def elaborate(self, platform):
        m = super().elaborate(platform)

        # formal must know that outputs are signed
        Up_out = Signal(signed(TEST_WIDTH))
        F_out = Signal(signed(TEST_WIDTH))
        m.d.comb += Up_out.eq(self.Up_out)
        m.d.comb += F_out.eq(self.F_out)

        config_bus_width = self.Config_Bus_top_in.shape().width
        Config_top_in = Signal(config_bus_width)
        m.d.comb += Config_top_in.eq(self.Config_Bus_top_in)
        
        # inputs - we test them in sequential mode
        m.d.comb += [
            self.lhs_in.eq(AnySeq(TEST_WIDTH)),
            self.rhs_in.eq(AnySeq(TEST_WIDTH)),
            self.F_in.eq(AnySeq(TEST_WIDTH)),

            # The Config Bus should take any value to
            # allow us to catch any logical/dependency
            # errors later on
            self.Config_Bus_top_in.eq(AnySeq(config_bus_width)),
            ]

        state_from_data = Signal(self.state.width)
        m.d.comb += state_from_data.eq(
            self.Config_Bus_top_in.Data[:state_from_data.width]
            )

        L_plus_R = Signal(signed(TEST_WIDTH))
        m.d.comb += L_plus_R.eq(self.lhs_in + self.rhs_in)

        L_plus_R_plus_F = Signal(signed(TEST_WIDTH))
        m.d.comb += L_plus_R_plus_F.eq(self.lhs_in + self.rhs_in + self.F_in)

        rst = ResetSignal()
        init = Initial()

        with m.If(init):
            m.d.comb += Assume(rst == 1)

        with m.Else():
            m.d.comb += Assume(rst == 0)
            m.d.comb += Assert(rst == 0)

            # check that config propagates on the next
            # cycle
            with m.If(Past(rst) == 0):
                m.d.comb += Assert(
                    self.Config_Bus_lhs_out == Past(Config_top_in)
                    )

                m.d.comb += Assert(
                    self.Config_Bus_rhs_out == Past(Config_top_in)
                    )

            with m.If(Past(rst) == 0):
                # verify the truth table on forward out
                with m.Switch(self.state):
                    with m.Case(ConfigForward.sum_l_r):
                        m.d.comb += Assert(F_out == L_plus_R)
                    with m.Case(ConfigForward.r):
                        m.d.comb += Assert(F_out == self.rhs_in)
                    with m.Case(ConfigForward.l):
                        m.d.comb += Assert(F_out == self.lhs_in)
                    with m.Default():
                        m.d.comb += Assert(F_out == 0)

                # verify the truth table on up out
                with m.Switch(Past(self.state)):
                    with m.Case(ConfigUp.sum_l_r):
                        m.d.comb += Assert(Up_out == Past(L_plus_R))
                    with m.Case(ConfigUp.sum_l_r_f):
                        m.d.comb += Assert(Up_out == Past(L_plus_R_plus_F))
                    with m.Case(ConfigUp.l):
                        m.d.comb += Assert(Up_out == Past(self.lhs_in))
                    with m.Case(ConfigUp.r):
                        m.d.comb += Assert(Up_out == Past(self.rhs_in))
                    with m.Default():
                        m.d.comb += Assert(Up_out == 0)
           
            
            with m.If(Past(rst) == 0):
                with m.If(Past(self.Config_Bus_top_in.En) == 1):
                    with m.If(Past(self.Config_Bus_top_in.Addr) == self.id_reg):
                        m.d.comb += Assert(
                            self.state == Past(state_from_data)
                        )

            # coverage check that signals have non trivial 
            # values
            m.d.comb += Cover(Past(self.state) >= 1)
            m.d.comb += Cover(self.F_out >= 0)
            m.d.comb += Cover(self.Up_out >= 0)
            m.d.comb += Cover(Past(state_from_data,2) == 1)

        return m

class TestAdderNode(FHDLTestCase):

    def test_formal(self):
        module = Driver()
        self.assertFormal(module, mode="bmc", depth=4)
        self.assertFormal(module, mode="cover", depth=4)

if __name__ == "__main__":
    unittest.main()
