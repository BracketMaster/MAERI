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

        # add submodule
        self.rn = rn = ReductionNetwork(     depth = depth,
                                        num_ports = num_ports,
                                        INPUT_WIDTH = INPUT_WIDTH, 
                                        bytes_in_line = bytes_in_line,
                                        VERBOSE=VERBOSE
                                    )

        # bytes in line should be a power of 2
        assert(divmod(log2(bytes_in_line),1)[1] == 0)

        # get needed parameters
        num_mults = len(rn.skeleton.mult_nodes)
        num_adders = len(rn.skeleton.adder_nodes)
        num_nodes = len(rn.skeleton.all_nodes)

        # address length should be a multiple of 8
        q, r = divmod(addr_shape,8)
        assert(r == 0)
        # we need this so that the increment_pc() function
        # call of each opcode functions properly
        opcodes.InitISA(_bytes_in_address=q,
                        _num_nodes=num_nodes,
                        _num_adders=num_adders,
                        _num_mults=num_mults
                        )

        # memory connections
        self.read_port = ReadPort(self.addr_shape, self.data_shape, 'read_port')
        self.write_port = WritePort(self.addr_shape, self.data_shape, 'write_port')
        prefix_record_name(self.read_port, 'comput_unit')
        prefix_record_name(self.write_port, 'comput_unit')

        # control connections
        self.start = Signal()
        self.status = Signal(State)
    
    def elaborate(self, platform):
        self.m = m = Module()

        m.submodules.rn = self.rn

        # allow for byte granularity within a memline
        # How many bits are needed to index into a memline?
        log2_bytes_in_mem_line = int(log2(self.bytes_in_line))

        mem_addr = Signal(self.addr_shape + log2_bytes_in_mem_line)
        mem_line_addr = mem_addr[log2_bytes_in_mem_line:]
        mem_line_byte_select = mem_addr[:log2_bytes_in_mem_line]

        pc = Signal.like(mem_addr)
        pc_line_addr = pc[log2_bytes_in_mem_line:]
        pc_line_byte_select = pc[:log2_bytes_in_mem_line]

        self.mem_data = mem_data = Array([Signal(8,name=f"mem_byte_{_}") for _ in range(self.bytes_in_line)])

        num_params = Signal(5)

        op = Signal(8)
        address = Signal(self.addr_shape)
        port_buffer = Signal(8)
        num_lines = Signal(8)
        len_runtime = Signal(8)

        state = self.status

        # mem read machinery
        # allows us to access the memory with a percieved
        # byte level granularity
        read_byte_ready = Signal(reset=1)
        read_rq = Signal()
        continue_read = Signal()
        addr_hold = Signal(self.addr_shape)
        last_addr = addr_hold

        condition_1 = Signal()
        condition_2 = Signal()
        mem_view = Signal(2)

        # TODO : remove 3 debug signals below
        m.d.comb += condition_1.eq(mem_line_byte_select == 0)
        m.d.comb += condition_2.eq(last_addr != mem_line_addr)
        m.d.comb += mem_view.eq(mem_line_byte_select)

        print(f"mem_line_addr shape = {mem_line_byte_select}")
        with m.If(read_rq | continue_read):
            # TODO : enable two signals below
            #condition_1 = (mem_line_byte_select == 0)
            #condition_2 = (last_addr != mem_line_addr)
            with m.If(condition_1 | condition_2 | continue_read):
                with m.FSM(name="FETCH_OPCODE"):
                    with m.State("BEGIN_READ"):
                        m.d.sync += continue_read.eq(1)
                        m.d.comb += read_byte_ready.eq(0)
                        m.d.comb += self.read_port.rq.eq(1)
                        m.d.comb += self.read_port.addr.eq(mem_line_addr)
                        m.d.sync += addr_hold.eq(mem_line_addr)
                        with m.If(self.read_port.rdy):
                            m.next = "FINISH_READ"
                
                    with m.State("FINISH_READ"):
                        m.d.comb += self.read_port.addr.eq(addr_hold)
                        with m.If(self.read_port.valid):
                            m.d.sync += continue_read.eq(0)
                            m.d.comb += mem_data[0].eq(self.read_port.data[0 : 8])
                            print(f"bytes_in_line = {self.bytes_in_line}")
                            for byte in range(1, self.bytes_in_line):
                                m.d.sync += mem_data[byte].eq(
                                    self.read_port.data[byte*8 : (byte + 1)*8]
                                    )
                            m.next = "BEGIN_READ"
                        with m.Else():
                            m.d.comb += read_byte_ready.eq(0)

        with m.FSM(name="MAERI_COMPUTE_UNIT_FSM"):
            with m.State("RESET"):
                m.d.comb += state.eq(State.reset)

                with m.If(self.start):
                    m.next = "FETCH_OP"

            with m.State("FETCH_OP"):
                m.d.comb += state.eq(State.fetch)

                # access memory with PC as the address
                m.d.comb += read_rq.eq(1)
                m.d.comb += mem_line_addr.eq(pc_line_addr)
                m.d.comb += mem_line_byte_select.eq(pc_line_byte_select)

                with m.If(read_byte_ready):
                    m.d.sync += op.eq(mem_data[pc_line_byte_select])

                    with m.Switch(mem_data[pc_line_byte_select]):
                        with m.Case(opcodes.Reset.op):
                            m.d.sync += pc.eq(0)
                            m.next = 'RESET'
                        with m.Case(opcodes.ConfigureStates.op):
                            m.d.sync += num_params.eq(opcodes.ConfigureStates.num_params())
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Case(opcodes.ConfigureWeights.op):
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Case(opcodes.LoadFeatures.op):
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Case(opcodes.StoreFeatures.op):
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Case(opcodes.Run.op):
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Default():
                            m.d.sync += pc.eq(0)
                            m.next = 'RESET'


            with m.State("FETCH_PARAMS"):
                param_counter = Signal(5)

                # access memory with PC as the address
                m.d.comb += read_rq.eq(1)
                m.d.comb += mem_line_addr.eq(pc_line_addr)
                m.d.comb += mem_line_byte_select.eq(pc_line_byte_select)

                with m.If(read_byte_ready):
                    m.d.sync += pc.eq(pc + 1)
                    m.d.sync += param_counter.eq(param_counter + 1)

                    # get address parameter
                    bytes_in_address = self.addr_shape // 8
                    for byte in range(bytes_in_address):
                            with m.If(param_counter == byte):
                                m.d.sync += address[byte*8 : (byte + 1)*8].eq(mem_data[pc_line_byte_select])

                    # get port address parameter
                    with m.If(param_counter == (bytes_in_address + 1)):
                        m.d.sync += port_buffer.eq(mem_data[pc_line_byte_select])

                        # get runtime length parameter
                        m.d.sync += port_buffer.eq(mem_data[pc_line_byte_select])

                    # get number of lines parameter
                    with m.If(param_counter == (bytes_in_address + 2)):
                        m.d.sync += num_lines.eq(mem_data[pc_line_byte_select])

                with m.If(param_counter == (num_params - 1)):
                    m.d.sync += param_counter.eq(0)
                    with m.Switch(op):
                        with m.Case(opcodes.ConfigureStates.op):
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
                            m.next = 'FETCH_OP'

            with m.State("CONFIGURE_STATES"):
                m.d.comb += state.eq(State.configure_states)

                # access memory with PC as the address
                m.d.comb += read_rq.eq(1)
                m.d.comb += mem_addr.eq(8)
                with m.If(read_byte_ready):
                    m.next = "FETCH_OP"

    

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
        self.status = Signal()
        self.controller = Top(
                    addr_shape = 24,
                    data_shape = 32,

                    depth = 6,
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
        init[0]  = 0x00_00_02_02
        init[1]  = 0x00_00_00_01
        init[2]  = 0xDE_AD_BE_EF

        config_test = []
        for node in range(16):
            test_vec = [randint(0,4) for node in range(4)]
            config_test += test_vec
            init[node + 3] = int.from_bytes(bytearray(test_vec), 'big')

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

            for tick in range(10):
                #print(f"tick = {tick}")
                #for index, sig in enumerate(dut.controller.mem_data):
                #    print(f"array[{index}] = {(yield sig)}")
                yield Tick()

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