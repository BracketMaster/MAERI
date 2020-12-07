from nmigen import Elaboratable, Module
from nmigen import Signal, Array, Cat

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort
from maeri.gateware.compute_unit.reduction_network import ReductionNetwork
from maeri.gateware.compute_unit.mem_adaptor import MemAdaptor
from maeri.compiler.assembler import opcodes

from enum import IntEnum, unique
from math import log2

@unique
class State(IntEnum):
    reset = 1
    configure_states = 2
    configure_weights = 3
    configure_collectors = 4
    configure_relus = 5
    load_features = 6
    store_features = 7
    run = 8
    debug = 9
    fetch = 10

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
        self.num_ports = num_ports
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
        self.mem_adaptor = MemAdaptor(
            bytes_in_line=bytes_in_line,
            addr_shape=addr_shape,
            data_shape=data_shape
            )
        self.read_port = self.mem_adaptor.read_port
        self.write_port = self.mem_adaptor.write_port

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
                        _num_ports=self.num_ports,
                        _num_adders=self.num_adders,
                        _num_mults=self.num_mults,
                        _input_width=INPUT_WIDTH
                        )

        # memory connections

        # control connections
        self.start = Signal()
        self.status = Signal(State)
    
    def elaborate(self, platform):
        self.m = m = Module()

        m.submodules.rn = self.rn
        m.submodules.mem_adaptor = mem_adaptor = self.mem_adaptor

        # allow for byte granularity within a memline
        # How many bits are needed to index into a memline?

        log2_bytes_in_mem_line = int(log2(self.bytes_in_line))
        pc = Signal.like(mem_adaptor.mem_addr)
        pc_line_addr = pc[log2_bytes_in_mem_line:]
        pc_line_byte_select = pc[:log2_bytes_in_mem_line]


        num_params = Signal(5)

        sync_op = Signal(opcodes.Opcodes)
        comb_op = Signal(opcodes.Opcodes)
        parsed_address = Signal(self.addr_shape)
        parsed_port_buffer = Signal(8)
        parsed_num_lines = Signal(8)
        parsed_len_runtime = Signal(8)

        state = self.status


        with m.FSM(name="MAERI_COMPUTE_UNIT_FSM"):
            with m.State("RESET"):
                m.d.comb += state.eq(State.reset)

                with m.If(self.start):
                    m.next = "FETCH_OP"

            with m.State("FETCH_OP"):
                m.d.comb += state.eq(State.fetch)

                # access memory with PC as the address
                m.d.comb += mem_adaptor.read_rq.eq(1)
                m.d.comb += mem_adaptor.mem_line_addr.eq(pc_line_addr)
                m.d.comb += mem_adaptor.mem_line_byte_select.eq(pc_line_byte_select)

                with m.If(mem_adaptor.read_byte_ready):
                    m.d.sync += sync_op.eq(mem_adaptor.byte_out)
                    m.d.comb += comb_op.eq(mem_adaptor.byte_out)

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
                        with m.Case(opcodes.ConfigureCollectors.op):
                            m.d.sync += num_params.eq(opcodes.ConfigureCollectors.num_params())
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
                m.d.comb += mem_adaptor.read_rq.eq(1)
                m.d.comb += mem_adaptor.mem_line_addr.eq(pc_line_addr)
                m.d.comb += mem_adaptor.mem_line_byte_select.eq(pc_line_byte_select)

                with m.If(mem_adaptor.read_byte_ready):
                    m.d.sync += pc.eq(pc + 1)
                    m.d.sync += param_counter.eq(param_counter + 1)

                    # get address parameter
                    bytes_in_address = self.addr_shape // 8
                    for byte in range(bytes_in_address):
                            with m.If(param_counter == byte):
                                m.d.sync += parsed_address[byte*8 : (byte + 1)*8]\
                                    .eq(mem_adaptor.byte_out)

                    # get port address parameter
                    with m.If(param_counter == (bytes_in_address + 1)):
                        m.d.sync += parsed_port_buffer.eq(mem_adaptor.byte_out)

                        # get runtime length parameter
                        m.d.sync += parsed_len_runtime.eq(mem_adaptor.byte_out)

                    # get number of lines parameter
                    with m.If(param_counter == (bytes_in_address + 2)):
                        m.d.sync += parsed_num_lines.eq(mem_adaptor.byte_out)

                    with m.If(param_counter == (num_params - 1)):
                        m.d.sync += param_counter.eq(0)
                        with m.Switch(sync_op):
                            with m.Case(opcodes.ConfigureStates.op):
                                m.next = 'CONFIGURE_STATES'
                            with m.Case(opcodes.ConfigureWeights.op):
                                m.next = 'CONFIGURE_WEIGHTS'
                            with m.Case(opcodes.ConfigureCollectors.op):
                                m.next = 'CONFIGURE_COLLECTORS'
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

                state_address_offset = Signal.like(self.rn.config_bus_ports[0].addr)
                state_node_offset = Signal.like(self.rn.config_bus_ports[0].addr)

                # access memory with parsed_address
                m.d.comb += mem_adaptor.mem_line_byte_select.eq(0)
                m.d.comb += mem_adaptor.mem_line_addr.eq(parsed_address + state_address_offset)

                assert(len(self.rn.config_bus_ports) == self.bytes_in_line)
                for index, port in enumerate(self.rn.config_bus_ports):
                    m.d.comb += port.data.eq(self.read_port.data[index*8 : (index + 1)*8])
                    m.d.comb += port.addr.eq(index + state_node_offset)
                
                iterations = -(-self.num_nodes//self.bytes_in_line)

                with m.If(mem_adaptor.read_byte_ready):
                    for port in self.rn.config_bus_ports:
                        m.d.comb += port.en.eq(1)
                        m.d.sync += state_address_offset.eq(state_address_offset + 1)
                        m.d.sync += state_node_offset.eq(state_node_offset + self.bytes_in_line)
                
                    
                    with m.If(state_address_offset == (iterations)):
                        m.d.sync += state_address_offset.eq(0)
                        m.d.sync += state_node_offset.eq(0)
                        m.next = "FETCH_OP"

                with m.If(state_address_offset != (iterations)):
                    m.d.comb += mem_adaptor.read_rq.eq(1)

            with m.State("CONFIGURE_WEIGHTS"):
                # this state configures the state of the mult nodes
                m.d.comb += state.eq(State.configure_weights)

                weight_address_offset = Signal.like(self.rn.config_bus_ports[0].addr)
                addr_shape = self.rn.config_bus_ports[0].addr.shape().width
                base_mem = (self.num_adders//self.bytes_in_line)*self.bytes_in_line
                weight_node_offset = Signal(addr_shape, reset = base_mem)

                # access memory with parsed_address
                m.d.comb += mem_adaptor.read_rq.eq(1)
                m.d.comb += mem_adaptor.mem_line_byte_select.eq(0)
                m.d.comb += mem_adaptor.mem_line_addr.eq(parsed_address + weight_address_offset)

                assert(len(self.rn.config_bus_ports) == self.bytes_in_line)
                for index, port in enumerate(self.rn.config_bus_ports):
                    m.d.comb += port.data.eq(self.read_port.data[index*8 : (index + 1)*8])
                    m.d.comb += port.addr.eq(index + weight_node_offset)
                
                iterations = -(-self.num_mults//self.bytes_in_line)

                with m.If(mem_adaptor.read_byte_ready):
                    for port in self.rn.config_bus_ports:
                        m.d.comb += port.en.eq(1)
                        m.d.comb += port.set_weight.eq(1)
                        m.d.sync += weight_address_offset.eq(weight_address_offset + 1)
                        m.d.sync += weight_node_offset.eq(weight_node_offset + self.bytes_in_line)
                
                
                    with m.If(weight_address_offset == (iterations)):
                        m.d.sync += weight_address_offset.eq(0)
                        m.d.sync += weight_node_offset.eq(self.num_adders)
                        m.next = "FETCH_OP"

                with m.If(weight_address_offset != (iterations)):
                    m.d.comb += mem_adaptor.read_rq.eq(1)

            with m.State("CONFIGURE_COLLECTORS"):
                # this state configures the state of the mult nodes
                m.d.comb += state.eq(State.configure_collectors)

                collect_address_offset = Signal.like(self.rn.select_output_node_ports[0])

                # access memory with parsed_address
                m.d.comb += mem_adaptor.read_rq.eq(1)
                m.d.comb += mem_adaptor.mem_line_byte_select.eq(0)
                m.d.comb += mem_adaptor.mem_line_addr.eq(parsed_address + collect_address_offset)

                chunked_port_selects = []
                num_chunks = self.rn.num_ports//self.bytes_in_line
                with m.If(mem_adaptor.read_byte_ready):
                    with m.If(collect_address_offset == (num_chunks - 1)):
                        m.d.sync += collect_address_offset.eq(0)
                        m.next = "FETCH_OP"
                    with m.Else():
                        m.d.sync += collect_address_offset.eq(collect_address_offset + 1)

                    for chunk in range(num_chunks):
                        with m.If(collect_address_offset == chunk):
                            port_slice = slice(chunk*self.bytes_in_line , (chunk + 1)*self.bytes_in_line)
                            port_slice_list = self.rn.select_output_node_ports[port_slice]
                            for index, select_port in enumerate(port_slice_list):
                                data_slice = slice(index*self.bytes_in_line , (index + 1)*self.bytes_in_line)
                                m.d.sync += select_port.eq(self.read_port.data[data_slice])

            with m.State("LOAD_FEATURES"):
                m.d.comb += state.eq(State.load_features)

            with m.State("STORE_FEATURES"):
                m.d.comb += state.eq(State.store_features)

            with m.State("DEBUG"):
                m.d.comb += state.eq(State.debug)

                # fecthed parameters
                start_address = 253
                # TODO : make this signal only two bits
                start_address_offset = 1
                length = 9#self.num_nodes

                # internal parameters
                # TODO : debug_counter would become the length of the
                # FIFO depth
                end_address_byte = (start_address << log2_bytes_in_mem_line) \
                    + (start_address_offset - 1) + length
                end_address_offset = end_address_byte & 3
                end_address_line = end_address_byte >> log2_bytes_in_mem_line
                print(f"start_address = {start_address}")
                print(f"start_address_offset = {start_address_offset}")
                print(f"end_address_line = {end_address_line}")
                print(f"end_address_offset = {end_address_offset}")

                with m.FSM(name="DEBUG_STORE"):
                    done = Signal()
                    with m.State("FIRST_WORD"):
                        first_word = Array([Signal(8,name=f"first_word_byte_{_}") 
                            for _ in range(self.bytes_in_line)])
                        m.d.comb += mem_adaptor.read_rq.eq(1)
                        m.d.comb += mem_adaptor.mem_line_addr.eq(start_address)

                        byte_counter = Signal(self.bytes_in_line)
                        m.d.comb += mem_adaptor.mem_line_byte_select.eq(byte_counter)

                        with m.If(mem_adaptor.read_byte_ready):
                            m.d.sync += byte_counter.eq(byte_counter + 1)
                            m.d.sync += first_word[byte_counter].eq(mem_adaptor.byte_out)

                            with m.If(byte_counter == (self.bytes_in_line - 1)):
                                m.d.sync += byte_counter.eq(0)
                                m.next = "LAST_WORD"

                    with m.State("LAST_WORD"):
                        last_word = Array([Signal(8,name=f"last_word_byte_{_}") 
                            for _ in range(self.bytes_in_line)])
                        m.d.comb += mem_adaptor.read_rq.eq(1)
                        m.d.comb += mem_adaptor.mem_line_addr.eq(end_address_line)

                        byte_counter = Signal(self.bytes_in_line)
                        m.d.comb += mem_adaptor.mem_line_byte_select.eq(byte_counter)

                        with m.If(mem_adaptor.read_byte_ready):
                            m.d.sync += byte_counter.eq(byte_counter + 1)
                            m.d.sync += last_word[byte_counter].eq(mem_adaptor.byte_out)

                            with m.If(byte_counter == (self.bytes_in_line - 1)):
                                m.d.sync += byte_counter.eq(0)
                                m.next = "STORE"
                    
                    with m.State("STORE"):
                        store_word = Array([Signal(8,name=f"store_word_byte_{_}") 
                            for _ in range(self.bytes_in_line)])
                        # TODO : change this as necessary
                        node_states = Array([node.state for node in (self.rn.adders + self.rn.mults)])
                        test_data = Array([_ for _ in range(10)])
                        data = node_states

                        num_words = end_address_line - start_address + 1
                        print(f"num_words = {num_words}")
                        word_counter = Signal(range(num_words))
                        # TODO : range parameter should be the cache length
                        byte_counter = Signal(range(64))
                        sub_word_select = byte_counter[:2]
                        with m.FSM(name="STORE_MACHINERY"):
                            with m.State("BUILD_WORD"):
                                with m.If((word_counter == 0) & (sub_word_select < start_address_offset)):
                                    m.d.sync += store_word[sub_word_select].eq(first_word[sub_word_select])
                                with m.Elif((word_counter == (num_words -1)) & (sub_word_select > end_address_offset)):
                                    m.d.sync += store_word[sub_word_select].eq(last_word[sub_word_select])
                                with m.Else():
                                    m.d.sync += store_word[sub_word_select].eq(data[byte_counter])
                                
                                m.d.sync += byte_counter.eq(byte_counter + 1)
                                with m.If(sub_word_select == (self.bytes_in_line - 1)):
                                    m.next = "START_WRITE"
                            
                            with m.State("START_WRITE"):
                                m.d.comb += self.write_port.addr.eq(start_address + word_counter)
                                m.d.comb += self.write_port.data.eq(Cat(store_word))
                                m.d.comb += self.write_port.rq.eq(1)
                                m.d.comb += self.write_port.en.eq(1)
                                m.next = "FINISH_WRITE"
                            
                            with m.State("FINISH_WRITE"):
                                m.d.comb += self.write_port.addr.eq(start_address + word_counter)
                                m.d.comb += self.write_port.data.eq(Cat(store_word))
                                m.d.comb += self.write_port.en.eq(1)
                                with m.If(self.write_port.ack):
                                    m.next = "BUILD_WORD"
                                    with m.If(word_counter == (num_words - 1)):
                                        m.d.comb += done.eq(1)
                                        m.d.sync += word_counter.eq(0)
                                        m.d.sync += byte_counter.eq(0)
                                    with m.Else():
                                        m.d.sync += word_counter.eq(word_counter + 1)

                        with m.If(done):
                            m.next = "FIRST_WORD"
                
                with m.If(done):
                    m.next = "FETCH_OP"
                    m.d.sync += pc.eq(pc + 1)

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