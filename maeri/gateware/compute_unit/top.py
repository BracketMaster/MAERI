from nmigen import Elaboratable, Module
from nmigen import Signal, Array

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort
from maeri.gateware.compute_unit.reduction_network import ReductionNetwork
from maeri.compiler.assembler import opcodes
from maeri.common.helpers import prefix_record_name

from enum import IntEnum, unique
from math import log2

@unique
class State(IntEnum):
    reset = 1
    configure_states = 2
    configure_weights = 3
    load_features = 4
    store_features = 5
    run = 6
    debug = 7
    fetch = 8

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
        self.rn = rn =\
             ReductionNetwork(  depth = depth,
                                num_ports = num_ports,
                                INPUT_WIDTH = INPUT_WIDTH, 
                                bytes_in_line = bytes_in_line,
                                VERBOSE=VERBOSE
                                )

        # bytes in line should be a power of 2
        assert(divmod(log2(bytes_in_line),1)[1] == 0)

        # get needed parameters
        self.num_mults = len(rn.skeleton.mult_nodes)
        self.num_adders = len(rn.skeleton.adder_nodes)
        self.num_nodes = len(rn.skeleton.all_nodes)

        # address length should be a multiple of 8
        q, r = divmod(addr_shape,8)
        assert(r == 0)
        # we need this so that the increment_pc() function
        # call of each opcode functions properly
        opcodes.InitISA(_bytes_in_address=q,
                        _num_nodes=self.num_nodes,
                        _num_adders=self.num_adders,
                        _num_mults=self.num_mults,
                        _input_width=INPUT_WIDTH
                        )

        # memory connections
        self.read_port = ReadPort(self.addr_shape, self.data_shape, 'read_port')
        self.write_port = WritePort(self.addr_shape, self.data_shape, 'write_port')
        prefix_record_name(self.read_port, 'compute_unit')
        prefix_record_name(self.write_port, 'compute_unit')

        # control connections
        self.start = Signal()
        self.status = Signal(State)
    
    def elaborate(self, platform):
        self.m = m = Module()

        m.submodules.rn = self.rn

        # allow for byte granularity within a memline
        # How many bits are needed to index into a memline?
        log2_bytes_in_mem_line = int(log2(self.bytes_in_line))


        pc = Signal.like(mem_addr)
        pc_line_addr = pc[log2_bytes_in_mem_line:]
        pc_line_byte_select = pc[:log2_bytes_in_mem_line]

        self.mem_data = mem_data = Array([Signal(8,name=f"mem_byte_{_}") for _ in range(self.bytes_in_line)])

        num_params = Signal(5)

        sync_op = Signal(opcodes.Opcodes)
        comb_op = Signal(opcodes.Opcodes)
        parsed_address = Signal(self.addr_shape)
        parsed_port_buffer = Signal(8)
        parsed_num_lines = Signal(8)
        parsed_len_runtime = Signal(8)

        state = self.status

        # mem read machinery
        # allows us to access the memory with a percieved
        # byte level granularity
        read_byte_ready = Signal(reset=1)
        read_rq = Signal()
        continue_read = Signal()
        addr_hold = Signal(self.addr_shape)
        last_addr = addr_hold
        mem_addr = Signal(self.addr_shape + log2_bytes_in_mem_line)
        mem_line_addr = mem_addr[log2_bytes_in_mem_line:]
        mem_line_byte_select = mem_addr[:log2_bytes_in_mem_line]

        with m.If(read_rq | continue_read):
            # TODO : enable two signals below
            condition_1 = (mem_line_byte_select == 0)
            condition_2 = (last_addr != mem_line_addr)
            with m.If(condition_1 | condition_2 | continue_read):
                with m.FSM(name="MEM_READ"):
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
                    m.d.sync += sync_op.eq(mem_data[pc_line_byte_select])
                    m.d.comb += comb_op.eq(mem_data[pc_line_byte_select])

                    with m.Switch(comb_op):
                        with m.Case(opcodes.Reset.op):
                            m.d.sync += pc.eq(0)
                            m.next = 'RESET'
                        with m.Case(opcodes.ConfigureStates.op):
                            m.d.sync += num_params.eq(opcodes.ConfigureStates.num_params())
                            m.d.sync += pc.eq(pc + 1)
                            m.next = 'FETCH_PARAMS'
                        with m.Case(opcodes.ConfigureWeights.op):
                            m.d.sync += num_params.eq(opcodes.ConfigureWeights.num_params())
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
                        with m.Case(opcodes.Debug.op):
                            m.next = 'DEBUG'
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
                                m.d.sync += parsed_address[byte*8 : (byte + 1)*8].eq(mem_data[pc_line_byte_select])

                    # get port address parameter
                    with m.If(param_counter == (bytes_in_address + 1)):
                        m.d.sync += parsed_port_buffer.eq(mem_data[pc_line_byte_select])

                        # get runtime length parameter
                        m.d.sync += parsed_len_runtime.eq(mem_data[pc_line_byte_select])

                    # get number of lines parameter
                    with m.If(param_counter == (bytes_in_address + 2)):
                        m.d.sync += parsed_num_lines.eq(mem_data[pc_line_byte_select])

                    with m.If(param_counter == (num_params - 1)):
                        m.d.sync += param_counter.eq(0)
                        with m.Switch(sync_op):
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
                # this state configures the state of the adder nodes
                # and the weight values of the mult nodes
                m.d.comb += state.eq(State.configure_states)

                state_address_offset = Signal.like(self.rn.config_ports_in[0].addr)
                state_node_offset = Signal.like(self.rn.config_ports_in[0].addr)

                # access memory with parsed_address
                m.d.comb += mem_line_byte_select.eq(0)
                m.d.comb += mem_line_addr.eq(parsed_address + state_address_offset)

                assert(len(self.rn.config_ports_in) == len(mem_data))
                for index, port in enumerate(self.rn.config_ports_in):
                    m.d.comb += port.data.eq(self.read_port.data[index*8 : (index + 1)*8])
                    m.d.comb += port.addr.eq(index + state_node_offset)
                
                iterations = -(-self.num_nodes//len(mem_data))

                with m.If(read_byte_ready):
                    for port in self.rn.config_ports_in:
                        m.d.comb += port.en.eq(1)
                        m.d.sync += state_address_offset.eq(state_address_offset + 1)
                        m.d.sync += state_node_offset.eq(state_node_offset + len(mem_data))
                
                    
                    with m.If(state_address_offset == (iterations)):
                        m.d.sync += state_address_offset.eq(0)
                        m.d.sync += state_node_offset.eq(0)
                        m.next = "FETCH_OP"

                with m.If(state_address_offset != (iterations)):
                    m.d.comb += read_rq.eq(1)

            with m.State("CONFIGURE_WEIGHTS"):
                # this state configures the state of the mult nodes
                m.d.comb += state.eq(State.configure_weights)

                weight_address_offset = Signal.like(self.rn.config_ports_in[0].addr)
                addr_shape = self.rn.config_ports_in[0].addr.shape().width
                base_mem = (self.num_adders//len(mem_data))*len(mem_data)
                weight_node_offset = Signal(addr_shape, reset = base_mem)

                # access memory with parsed_address
                m.d.comb += read_rq.eq(1)
                m.d.comb += mem_line_byte_select.eq(0)
                m.d.comb += mem_line_addr.eq(parsed_address + weight_address_offset)

                assert(len(self.rn.config_ports_in) == len(mem_data))
                for index, port in enumerate(self.rn.config_ports_in):
                    m.d.comb += port.data.eq(self.read_port.data[index*8 : (index + 1)*8])
                    m.d.comb += port.addr.eq(index + weight_node_offset)
                
                iterations = -(-self.num_mults//len(mem_data))

                with m.If(read_byte_ready):
                    for port in self.rn.config_ports_in:
                        m.d.comb += port.en.eq(1)
                        m.d.comb += port.set_weight.eq(1)
                        m.d.sync += weight_address_offset.eq(weight_address_offset + 1)
                        m.d.sync += weight_node_offset.eq(weight_node_offset + len(mem_data))
                
                
                    with m.If(weight_address_offset == (iterations)):
                        m.d.sync += weight_address_offset.eq(0)
                        m.d.sync += weight_node_offset.eq(self.num_adders)
                        m.next = "FETCH_OP"

                with m.If(weight_address_offset != (iterations)):
                    m.d.comb += read_rq.eq(1)

            with m.State("LOAD_FEATURES"):
                m.d.comb += state.eq(State.load_features)

            with m.State("STORE_FEATURES"):
                m.d.comb += state.eq(State.store_features)

            with m.State("DEBUG"):
                debug_length = 2#self.num_nodes
                debug_counter = Signal(range(debug_length))

                m.d.comb += state.eq(State.debug)

                with m.If(debug_counter == (debug_length - 1)):
                    m.d.sync += pc.eq(pc + 1)
                    m.d.sync += debug_counter.eq(0)
                    m.next = "FETCH_OP"
                with m.Else():
                    m.d.sync += debug_counter.eq(debug_counter + 1)

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