"""
Instantiate a MAERI hardware tree to play
around with.

This file does a dot product on a MAERI
tree of depth 4 while using adder states
l, r, sum_l_r, sum_l_r_f.

This file only test the ability of a forwarding
link to forward to the right.
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

r = lambda : (random() - .5)

# products for node 7 and 14 must be 0 so that the
# maeri adder tree only sums the inner four nodes
vec_a_fp = [0, r(), r(), r(), r(), r(), r(), 0]
vec_b_fp = [r(), r(), r(), r(), r(), r(), r(), r()]
intermediate = [i1*i2 for i1,i2 in zip(vec_a_fp, vec_b_fp)]

# we only sum the inner four nodes since the hardware
# will be confgured to ignore results from nodes 8
# 13 during reduction, and products from node 7 and 
# 14 are fixed to zero because both vec_a_fp[0] and 
# vec_a_fp[-1] equal 0
golden_dot_fp = sum(intermediate[2:-2])


# inspect
print(" ==== FLOATING POINT ==== ")
print(f"vec_a_fp = {vec_a_fp}")
print(f"vec_b_fp = {vec_b_fp}")
print(f"vec_a_fp . vec_b_fp = {golden_dot_fp}")
print()

dut = Maeri(depth=4, num_ports=4, INPUT_WIDTH=WIDTH)
nodes = dut.skeleton.all_nodes

# convert to fixed point 8 for use in hardware
vec_a_f8 = [cast_f_to_f8(val) for val in vec_a_fp]
vec_b_f8 = [cast_f_to_f8(val) for val in vec_b_fp]

# re-useables
def configure_node(node, Data, Inject_En):
    config_port = dut.skeleton.node_v_port[node]
    yield dut.config_ports[config_port].En.eq(1)
    yield dut.config_ports[config_port].Addr.eq(node.id)
    yield dut.config_ports[config_port].Data.eq(Data)
    yield dut.config_ports[config_port].Inject_En.eq(Inject_En)

def process():
    # set collect port to collect from node 0
    # and node 4. The values should actually be
    # the same with a delay of 2
    yield dut.select_ports[0].eq(0)
    yield dut.select_ports[1].eq(5)

    # set leave weights
    yield from configure_node(nodes[7], vec_a_f8[0], 0)
    yield from configure_node(nodes[11], vec_a_f8[4], 0)
    yield Tick()

    yield from configure_node(nodes[8], vec_a_f8[1], 1)
    yield from configure_node(nodes[12], vec_a_f8[5], 1)
    yield Tick()

    yield from configure_node(nodes[9], vec_a_f8[2], 0)
    yield from configure_node(nodes[13], vec_a_f8[6], 0)
    yield Tick()

    yield from configure_node(nodes[10], vec_a_f8[3], 1)
    yield from configure_node(nodes[14], vec_a_f8[7], 1)
    yield Tick()

    # configure adder nodes
    yield from configure_node(nodes[2], ConfigUp.sum_l_r, 0)
    yield from configure_node(nodes[3], ConfigUp.l, 0)
    yield from configure_node(nodes[4], ConfigForward.sum_l_r, 0)
    yield from configure_node(nodes[5], ConfigUp.sum_l_r_f, 0)
    yield from configure_node(nodes[6], ConfigUp.r, 0)
    yield Tick()

    yield from configure_node(nodes[1], ConfigUp.l, 0)
    yield Tick()

    yield from configure_node(nodes[0], ConfigUp.sum_l_r, 0)
    yield Tick()

    # start injecting data over which to perform
    # computation
    for inject_val, port in zip(vec_b_f8[::2], dut.inject_ports):
        yield port.eq(inject_val)
    yield Tick()

    for inject_val, port in zip(vec_b_f8[1::2], dut.inject_ports):
        yield port.eq(inject_val)
    yield Tick()

    yield Tick()
    yield Tick()
    yield from print_sig(dut.collect_ports[1], format=cast_f8_to_f)

    # allow value to propagate to collection port
    for tick in range(2):
        yield Tick()
    
    yield from print_sig(dut.collect_ports[0], format=cast_f8_to_f)


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