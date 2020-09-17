"""
Instantiate a MAERI hardware tree to play
around with.

This file does a dot product on a MAERI
tree of depth 3
"""
from numpy import array

from nmigen import Module
from nmigen.sim.pysim import Simulator, Delay, Settle
from nmigen.sim.pysim import Tick

from maeri.gateware.core.maeri_hw import Maeri
from maeri.gateware.printsig import print_sig
from maeri.common.enums import ConfigUp, ConfigForward
from maeri.compiler.casts import cast_fixed_to_float
from maeri.compiler.casts import cast_float_to_fixed

from random import random

WIDTH = 8

# casting functions
cast_f_to_f8 = cast_float_to_fixed(WIDTH, numpy=False)
cast_f8_to_f = cast_fixed_to_float(WIDTH)

# golden floating point result
vec_a_fp = [.5*(random()*2 - 1) for i in range(4)]
vec_b_fp = [.5*(random()*2 - 1) for i in range(4)]
golden_dot_fp = sum(
    [i1*i2 for i1,i2 in zip(vec_a_fp, vec_b_fp)])

# golden fixed point result
vec_a_f8 = [cast_f_to_f8(val) for val in vec_a_fp]
vec_b_f8 = [cast_f_to_f8(val) for val in vec_b_fp]

# inspect
print(" ==== FLOATING POINT ==== ")
print(f"vec_a_fp = {vec_a_fp}")
print(f"vec_b_fp = {vec_b_fp}")
print(f"vec_a_fp . vec_b_fp = {golden_dot_fp}")
print()

dut = Maeri(depth=3, num_ports=2, INPUT_WIDTH=WIDTH)
nodes = dut.skeleton.all_nodes

# re-useables
def configure_node(node, Data, Inject_En):
    config_port = dut.skeleton.node_v_port[node]
    yield dut.config_ports[config_port].En.eq(1)
    yield dut.config_ports[config_port].Addr.eq(node.id)
    yield dut.config_ports[config_port].Data.eq(Data)
    yield dut.config_ports[config_port].Inject_En.eq(Inject_En)

def process():
    # set collect port to collect from node 0
    yield dut.select_ports[0].eq(0)

    # configure mult nodes 3 and 5
    yield from configure_node(nodes[3], vec_a_f8[0], 0)
    yield from configure_node(nodes[5], vec_a_f8[2], 0)
    yield Tick()

    # configure mult nodes 4 and 6
    yield from configure_node(nodes[4], vec_a_f8[1], 1)
    yield from configure_node(nodes[6], vec_a_f8[3], 1)
    yield Tick()

    # configure adders
    yield from configure_node(nodes[0], ConfigUp.sum_l_r, 1)
    yield from configure_node(nodes[1], ConfigUp.sum_l_r, 1)
    yield from configure_node(nodes[2], ConfigUp.sum_l_r, 1)

    yield Tick()

    # disable configuration
    for port in dut.config_ports:
        yield port.eq(0)
    yield Tick()

    # allow config to propagate to mults before
    # beginning computation
    for tick in range(2):
        yield Tick()

    # inject vectors for simulation
    yield dut.inject_ports[0].eq(vec_b_f8[0])
    yield dut.inject_ports[1].eq(vec_b_f8[2])
    yield Tick()

    yield dut.inject_ports[0].eq(vec_b_f8[1])
    yield dut.inject_ports[1].eq(vec_b_f8[3])
    yield Tick()

    # inject 0 effectively disabling injection
    yield dut.inject_ports[0].eq(0)
    yield dut.inject_ports[1].eq(0)
    yield Tick()

    # allow sum to propagate
    yield Tick()

    # print result
    yield Settle()
    val = cast_f8_to_f((yield dut.collect_ports[0]))
    print(f"dut.collect_ports[0] = {val}")

# set up simulation
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