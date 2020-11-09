from nmigen import Elaboratable, Module
from nmigen import Signal

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort
from maeri.gateware.compute_unit.status import Status
from maeri.gateware.compute_unit.reduction_network import ReductionNetwork
from maeri.compiler.ISA.opcodes import Opcodes
from maeri.common.helpers import prefix_record_name

from enum import IntEnum, unique

@unique
class State(IntEnum):
    IDLE = 0
    CONFIGURE_STATES = 1
    CONFIGURE_WEIGHTS = 2
    LOAD_FEATURES = 3
    STORE_FEATURES = 4
    RUN = 5

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

        # memory connections
        self.read_port = ReadPort(self.addr_shape, self.data_shape, 'read_port')
        self.write_port = WritePort(self.addr_shape, self.data_shape, 'write_port')
        prefix_record_name(self.read_port, 'comput_unit')
        prefix_record_name(self.write_port, 'comput_unit')

        # control connections
        self.start = Signal()
        self.status = Signal(Status)

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

        pc = Signal(self.addr_shape)
        op = Signal(self.data_shape)

        curr_state = Signal(5)
        past_state = Signal(5)
        m.d.sync += past_state.eq(curr_state)

        with m.FSM(name="MAERI_COMPUTE_UNIT_FSM"):
            with m.State("IDLE"):
                m.d.comb += curr_state.eq(State.IDLE)

                with m.Switch(op):
                    with m.Case(Opcodes.configure_states):
                        m.next = 'CONFIGURE_STATES'
                    with m.Case(Opcodes.configure_weights):
                        m.next = 'CONFIGURE_WEIGHTS'
                    with m.Case(Opcodes.load_features):
                        m.next = 'LOAD_FEATURES'
                    with m.Case(Opcodes.store_features):
                        m.next = 'STORE_FEATURES'
                    with m.Case(Opcodes.run):
                        m.next = 'RUN'
                    with m.Default():
                        m.next = 'IDLE'

                with m.FSM(name="FETCH_OPCODE"):
                    with m.State("BEGIN_READ"):
                        m.d.comb += self.read_port.rq.eq(1)
                        m.d.comb += self.read_port.addr.eq(pc)
                        with m.If(self.read_port.rdy):
                            m.next = "FINISH_READ"
                
                    with m.State("FINISH_READ"):
                        m.d.comb += self.read_port.addr.eq(pc)
                        with m.If(self.read_port.valid):
                            m.d.sync += pc.eq(pc + 1)
                            m.d.comb += op.eq(self.read_port.data)
                            m.next = "BEGIN_READ"
            
            with m.State("CONFIGURE_STATES"):
                m.d.comb += curr_state.eq(State.CONFIGURE_STATES)
                m.d.comb += self.status.eq(Status.configuring)
                m.next = "IDLE"

                #m.d.sync += self.reset_op(op)

            with m.State("CONFIGURE_WEIGHTS"):
                m.d.comb += curr_state.eq(State.CONFIGURE_WEIGHTS)
                m.d.comb += self.status.eq(Status.configuring)

                #m.d.sync += self.reset_op(op)

            with m.State("LOAD_FEATURES"):
                m.d.comb += curr_state.eq(State.LOAD_FEATURES)
                m.d.comb += self.status.eq(Status.loading)

                #m.d.sync += self.reset_op(op)

            with m.State("STORE_FEATURES"):
                m.d.comb += curr_state.eq(State.STORE_FEATURES)
                m.d.comb += self.status.eq(Status.storing)

                #m.d.sync += self.reset_op(op)

            with m.State("RUN"):
                m.d.comb += curr_state.eq(State.RUN)
                m.d.comb += self.status.eq(Status.running)

                #m.d.sync += self.reset_op(op)
        
        return m

    def reset_op(self, op):
        return [op.eq(0)]
    
    def ports(self):
        ports = []
        ports += [self.start]
        ports += [self.status]
        ports += [self.read_port[sig] for sig in self.read_port.fields]
        ports += [self.write_port[sig] for sig in self.write_port.fields]
        ports += self.rn.ports()

        return ports

class Sim(Elaboratable):
    def __init__(self):
        from maeri.gateware.platform.sim.mem import Mem
        from random import randint

        self.start = Signal()
        self.status = Signal(Status)
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
        init[0]  = Opcodes.configure_states
        init[1] = 0
        init[2] = 0
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



if __name__ == "__main__":
    from nmigen.sim import Simulator, Tick

    def process():
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