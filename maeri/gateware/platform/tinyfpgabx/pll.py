from nmigen import Signal, ClockSignal, ResetSignal
from nmigen import Instance, ClockDomain, Elaboratable
from nmigen import Module, Const

class Pll(Elaboratable):
    """ Creates clock domains for the TinyFPGA Bx. """

    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        locked_compute = Signal()
        clk_compute  = Signal()

        # Create our domains...
        m.domains.compute   = ClockDomain()

        # ... create our 48 MHz IO and 12 MHz USB clock...
        m.submodules.pll = Instance("SB_PLL40_CORE",
            # parameters
            p_FEEDBACK_PATH = "SIMPLE",
            p_DIVR          = 0,
            p_DIVF          = 47,
            p_DIVQ          = 4,
            p_FILTER_RANGE  = 1,

            # inputs / outputs
            o_LOCK          = locked_compute,
            i_RESETB        = Const(1),
            i_BYPASS        = Const(0),
            i_REFERENCECLK  = ref_clk,
            o_PLLOUTCORE   = clk_compute,

        )

        # ... and constrain them to their new frequencies.
        platform.add_clock_constraint(clk_compute, 48e6)

        # We'll use our 48MHz clock for everything _except_ the usb domain...
        m.d.comb += [
            ClockSignal("compute")     .eq(clk_compute),
            ResetSignal("compute")    .eq(~locked_compute)
        ]

        return m