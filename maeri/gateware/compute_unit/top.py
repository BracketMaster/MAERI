from nmigen import Elaboratable, Module
from nmigen import Signal, Array

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort
from maeri.gateware.compute_unit.reduction_network import ReductionNetwork
from maeri.compiler.ISA import opcodes
from maeri.common.helpers import prefix_record_name

from enum import IntEnum, unique

from math import log2

@unique
class State(IntEnum):
    reset = 1
    fetch = 2
    configure_states = 3
    configure_weights = 4
    load_features = 5
    store_features = 6
    run = 7

class Top(Elaboratable):

    def __init__(   self,
                    addr_shape,
                    data_shape,

                    depth,
                    num_ports,
                    INPUT_WIDTH,
                    bytes_in_line,
                    VERBOSE=False
                    ):
        self.addr_shape = addr_shape
        self.data_shape = data_shape
        self.bytes_in_line = bytes_in_line

        # bytes in line should be a power of 2
        assert(divmod(log2(bytes_in_line),1)[1] == 0)

        # address length should be a multiple of 8
        q, r = divmod(addr_shape,8)
        assert(r == 0)
        # we need this so that the increment_pc() function
        # call of each opcode functions properly
        opcodes.InitISA(_bytes_in_address=q)

        # memory connections
        self.read_port = ReadPort(self.addr_shape, self.data_shape, 'read_port')
        self.write_port = WritePort(self.addr_shape, self.data_shape, 'write_port')
        prefix_record_name(self.read_port, 'comput_unit')
        prefix_record_name(self.write_port, 'comput_unit')

        # control connections
        self.start = Signal()

        # add submodule
        self.rn = ReductionNetwork(     depth = depth,
                                        num_ports = num_ports,
                                        INPUT_WIDTH = INPUT_WIDTH, 
                                        bytes_in_line = bytes_in_line,
                                        VERBOSE=VERBOSE
                                    )
    
    def elaborate(self, platform):
        self.m = m = Module()

        m.submodules.rn = self.rn

        # allow for byte granularity within a memline
        # How many bits are needed to index into a memline?
        log2_bytes_in_mem_line = int(log2(self.bytes_in_line))

        pc = Signal(self.addr_shape + log2_bytes_in_mem_line)
        pc_line_addr = pc[log2_bytes_in_mem_line:]
        pc_byte_addr = pc[:log2_bytes_in_mem_line]

        mem_addr = Signal(self.addr_shape + log2_bytes_in_mem_line)
        mem_line_addr = mem_addr[log2_bytes_in_mem_line:]
        mem_byte_addr = mem_addr[:log2_bytes_in_mem_line]

        mem_data = Array([Signal(8,name=f"mem_byte_{_}") for _ in range(self.bytes_in_line)])

        op = Signal(8)

        state = Signal(State)

        with m.FSM(name="MAERI_COMPUTE_UNIT_FSM"):
            with m.State("RESET"):
                m.d.comb += state.eq(State.reset)

                with m.If(self.start):
                    m.next = "FETCH"

            with m.State("FETCH"):
                m.d.comb += state.eq(State.fetch)

                with m.Switch(op):
                    with m.Case(opcodes.Reset.op):
                        m.d.sync += pc.eq(0)
                        m.next = 'RESET'
                    with m.Case(opcodes.ConfigureStates.op):
                        m.d.sync += pc.eq(pc + opcodes.ConfigureStates.increment_pc())
                        m.next = 'CONFIGURE_STATES'
                    with m.Case(opcodes.ConfigureWeights.op):
                        m.next = 'CONFIGURE_WEIGHTS'
                    with m.Case(opcodes.LoadFeatures.op):
                        m.next = 'LOAD_FEATURES'
                    with m.Case(opcodes.StoreFeatures.op):
                        m.next = 'STORE_FEATURES'
                    with m.Case(opcodes.Run.op):
                        m.next = 'RUN'
                    with m.Default():
                        m.next = 'FETCH'

                with m.If(pc_byte_addr == 0):
                    with m.FSM(name="FETCH_OPCODE"):
                        with m.State("BEGIN_READ"):
                            m.d.comb += self.read_port.rq.eq(1)
                            m.d.comb += self.read_port.addr.eq(pc_line_addr)
                            with m.If(self.read_port.rdy):
                                m.next = "FINISH_READ"
                    
                        with m.State("FINISH_READ"):
                            m.d.comb += self.read_port.addr.eq(pc_line_addr)
                            with m.If(self.read_port.valid):
                                for byte in range(self.bytes_in_line):
                                    m.d.sync += mem_data[byte].eq(
                                        self.read_port.data[byte*8 : (byte + 1)*8]
                                        )
                                m.d.comb += op.eq(self.read_port.data)
                                m.next = "BEGIN_READ"
                with m.Else():
                    m.d.comb += op.eq(mem_data[pc_byte_addr])

            with m.State("CONFIGURE_STATES"):
                m.d.comb += state.eq(State.configure_states)

                m.next = "FETCH"

            with m.State("CONFIGURE_WEIGHTS"):
                m.d.comb += state.eq(State.configure_weights)

            with m.State("LOAD_FEATURES"):
                m.d.comb += state.eq(State.load_features)

            with m.State("STORE_FEATURES"):
                m.d.comb += state.eq(State.store_features)

            with m.State("RUN"):
                m.d.comb += state.eq(State.run)
        
        return m
    
    def ports(self):
        ports = []
        ports += [self.start]
        ports += [self.read_port[sig] for sig in self.read_port.fields]
        ports += [self.write_port[sig] for sig in self.write_port.fields]
        ports += self.rn.ports()

        return ports

class Sim(Elaboratable):
    def __init__(self):
        from maeri.gateware.platform.sim.mem import Mem
        from random import randint

        self.start = Signal()
        self.controller = Top(
                    addr_shape = 24,
                    data_shape = 32,

                    depth = 5,
                    num_ports = 4,
                    INPUT_WIDTH = 8, 
                    bytes_in_line = 4,
                    VERBOSE=True
                )

        # attach mem
        width = 32
        depth = 256
        max_val = 255
        init = [randint(0, max_val) for val in range(0, depth)]
        init[0]  = opcodes.ConfigureStates.op
        init[1] = opcodes.ConfigureStates.op
        init[2] = opcodes.Reset.op

        self.mem = Mem(width=width, depth=depth, init=init)
    
    def elaborate(self, platform):
        m = Module()
        m.submodules.controller = controller = self.controller
        m.submodules.mem = mem = self.mem

        m.d.comb += controller.read_port.connect(mem.read_port1)
        m.d.comb += mem.write_port1.connect(controller.write_port)

        m.d.comb += controller.start.eq(self.start)

        return m



if __name__ == "__main__":
    from nmigen.sim import Simulator, Tick

    def process():
        yield dut.start.eq(1)
        yield Tick()
        yield dut.start.eq(0)
        yield Tick()

        for tick in range(10):
            yield Tick()

    dut = Sim()
    sim = Simulator(dut, engine="pysim")
    sim.add_clock(1e-6)
    sim.add_sync_process(process)

    with sim.write_vcd(f"{__file__[:-3]}.vcd"):
        sim.run()

    #top = Top(
    #            addr_shape = 24,
    #            data_shape = 32,

    #            depth = 5,
    #            num_ports = 4,
    #            INPUT_WIDTH = 8, 
    #            bytes_in_line = 4,
    #            VERBOSE=True
    #        )

    ## generate verilog
    #from nmigen.back import verilog
    #name = __file__[:-3]
    #f = open(f"{name}.v", "w")
    #f.write(verilog.convert(top, 
    #    name = name,
    #    strip_internal_attrs=True,
    #    ports=top.ports())
    #)