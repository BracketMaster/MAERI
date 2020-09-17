from nmigen import Module
from nmigen.sim.pysim import Simulator, Delay, Settle
from nmigen.sim.pysim import Tick

from maeri.gateware.core.mult_node import MultNode
from maeri.gateware.printsig import print_sig

ID = 1
WIDTH = 8

def process():
    # configure mult to take features from
    # injector
    yield dut.Config_Bus_top_in.En.eq(1)
    yield dut.Config_Bus_top_in.Addr.eq(ID)
    yield dut.Config_Bus_top_in.Data.eq(100)
    yield dut.Config_Bus_top_in.Inject_En.eq(1)
    yield Tick()

    yield dut.Inject_in.eq(-100)
    yield dut.Config_Bus_top_in.En.eq(0)
    yield Tick()

    yield Settle()
    yield from print_sig(dut.Up_out)

    # configure mult to take features from
    # forward_in
    yield dut.Config_Bus_top_in.En.eq(1)
    yield dut.Config_Bus_top_in.Addr.eq(ID)
    yield dut.Config_Bus_top_in.Data.eq(100)
    yield dut.Config_Bus_top_in.Inject_En.eq(0)
    yield Tick()

    yield dut.F_in.eq(-70)
    yield dut.Config_Bus_top_in.En.eq(0)
    yield Tick()

    yield Settle()
    yield from print_sig(dut.Up_out)




dut = MultNode(ID=1, INPUT_WIDTH=WIDTH)
m = Module()
m.submodules.dut = dut
sim = Simulator(m)
sim.add_clock(1/(1e9), domain="sync")
sim.add_process(process)

my_sim = sim.write_vcd(
    f"{__file__[:-3]}.vcd", 
    f"{__file__[:-3]}.gtkw",
    traces=dut.ports()
    )
with my_sim:
    sim.run()