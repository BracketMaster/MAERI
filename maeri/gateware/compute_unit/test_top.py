from maeri.gateware.compute_unit.top import Top
from nmigen import Elaboratable, Module
from nmigen import Signal, Array
from maeri.gateware.platform.sim.mem import Mem
from random import randint

from maeri.compiler.assembler.signs import to_unsigned

class Sim(Elaboratable):
    def __init__(self):

        self.start = Signal()
        self.status = Signal()
        self.controller = Top(
                    addr_shape = 24,
                    data_shape = 32,

                    depth = 6,
                    num_ports = 16,
                    INPUT_WIDTH = 8, 
                    bytes_in_line = 4,
                    VERBOSE=True
                )

        # attach mem
        width = 32
        depth = 256
        max_val = 255

        init = [randint(0, max_val) for val in range(0, depth)]
        init[0]  = 0x00_00_04_02
        init[1]  = 0x00_00_14_03
        init[2]  = 0x00_00_00_01
        init[3]  = 0xDE_AD_BE_EF
        
        self.config_state_test_vec =  \
            [randint(0,4) for adder in range(self.controller.num_adders)] +\
            [randint(0,1) for mult in range(self.controller.num_mults)]
        for mem_line in range(16):
            array = self.config_state_test_vec[mem_line*4 : (mem_line + 1)*4]
            init[mem_line + 4] = int.from_bytes(bytearray(array), 'little')
        
        self.config_weight_test_vec = \
            [0 ,0, 0] +\
            [randint(-128, 127) for mult in range(self.controller.num_mults)]
        for mem_line in range(17):
            array = self.config_weight_test_vec[mem_line*4 : (mem_line + 1)*4]
            array = [to_unsigned(el, 8) for el in array]
            init[mem_line + 20] = int.from_bytes(bytearray(array), 'little')
        self.config_weight_test_vec = self.config_weight_test_vec[3:]
        
        self.mem = Mem(width=width, depth=depth, init=init)
    
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

            for tick in range(80):
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
            print(dut.config_state_test_vec[:len(actual_state_config)])
            assert(dut.config_state_test_vec[:len(actual_state_config)] == actual_state_config)

            actual_weight_config = []
            for node in mult_nodes:
                actual_weight_config += [(yield node.weight)]

            print()
            print("ACTUAL WEIGHT CONFIG")
            print(actual_weight_config)
            print("EXPECTED WEIGHT CONFIG")
            print(dut.config_weight_test_vec[:len(actual_weight_config)])
            assert(dut.config_weight_test_vec[:len(actual_weight_config)] == actual_weight_config)

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