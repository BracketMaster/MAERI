from maeri.gateware.compute_unit.top import Top
from maeri.gateware.platform.sim.mem import Mem
from maeri.compiler.assembler.assemble import assemble

from nmigen import Signal, Array
from nmigen import Elaboratable, Module

from maeri.compiler.assembler.states import ConfigForward, ConfigUp
from maeri.compiler.assembler import opcodes
from maeri.compiler.assembler.opcodes import LoadFeatures
from maeri.compiler.assembler.states import InjectEn
from random import randint, choice


class Sim(Elaboratable):
    def __init__(self):

        self.start = Signal()
        self.status = Signal()
        self.controller = controller =\
             Top(
                    addr_shape = 24,
                    data_shape = 32,

                    depth = 6,
                    num_ports = 16,
                    INPUT_WIDTH = 8, 
                    bytes_in_line = 4,
                    VERBOSE=False
                )

        # build out ops
        valid_adder_states = [ConfigForward.sum_l_r, ConfigForward.r, ConfigForward.l]
        valid_adder_states += [ConfigUp.sum_l_r, ConfigUp.r, ConfigUp.l, ConfigUp.sum_l_r_f]
        valid_mult_states = [InjectEn.on, InjectEn.off]

        ops = []

        test_state_vec_1 = [choice(valid_adder_states) for node in range(controller.num_adders)]
        test_state_vec_1 += [choice(valid_mult_states) for node in range(controller.num_mults)]
        ops += [opcodes.ConfigureStates(test_state_vec_1)]

        test_weight_vec_1 = [randint(-128, 127) for node in range(controller.num_mults)]
        ops += [opcodes.ConfigureWeights(test_weight_vec_1)]
        ops += [opcodes.Debug()]

        # assemble ops
        init = assemble(ops)

        # attach and initialize mem
        width = 32
        depth = 256
        self.mem = Mem(width=width, depth=depth, init=init)

        # for testing later in sim
        self.test_state_vec_1 = [int(el) for el in test_state_vec_1]
        self.test_weight_vec_1 = [int(el) for el in test_weight_vec_1]
    
    def elaborate(self, platform):
        m = Module()
        m.submodules.controller = controller = self.controller
        m.submodules.mem = mem = self.mem

        m.d.comb += controller.read_port.connect(mem.read_port1)
        m.d.comb += mem.write_port1.connect(controller.write_port)

        m.d.comb += controller.start.eq(self.start)
        m.d.comb += self.status.eq(controller.status)

        return m
    
    def ports(self):
        return [self.start, self.status]



if __name__ == "__main__":
    if True:
        from nmigen.sim import Simulator, Tick

        def process():
            yield dut.start.eq(1)
            yield Tick()
            yield dut.start.eq(0)
            yield Tick()

            for tick in range(120):
                yield Tick()

            # list of states
            all_nodes = dut.controller.rn.adders + dut.controller.rn.mults
            mult_nodes = dut.controller.rn.mults

            actual_state_config = []
            for node in all_nodes:
                actual_state_config += [(yield node.state)]
            
            print()
            print("ACTUAL STATE CONFIG")
            print(actual_state_config)
            print("EXPECTED STATE CONFIG")
            print(dut.test_state_vec_1)
            assert(actual_state_config == dut.test_state_vec_1)

            actual_weight_config = []
            for node in mult_nodes:
                actual_weight_config += [(yield node.weight)]

            print()
            print("ACTUAL WEIGHT CONFIG")
            print(actual_weight_config)
            print("EXPECTED WEIGHT CONFIG")
            print(dut.test_weight_vec_1)
            assert(actual_weight_config == dut.test_weight_vec_1)

        dut = Sim()
        sim = Simulator(dut, engine="pysim")
        sim.add_clock(1e-6)
        sim.add_sync_process(process)

        with sim.write_vcd(f"{__file__[:-3]}.vcd"):
            sim.run()
    else:
        top = Sim()

        # generate verilog
        from nmigen.back import verilog
        name = __file__[:-3]
        f = open(f"{name}.v", "w")
        f.write(verilog.convert(top, 
            name = name,
            strip_internal_attrs=True,
            ports=top.ports())
        )
