from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable
from maeri.gateware.platform.generic.interfaces import WritePort, ReadPort
from sdram_controller import sdram_controller

def led_display_value(m, led, value):
    value = Const(value, 8)
    statements = [light.eq(val) for light,val in zip(led, value)]
    return statements

def led_display_signal(m, led, signal):
    return [light.eq(sig) for light,sig in zip(led,signal)]

class Mem(Elaboratable):
    def __init__(self):
        """
        A memory with two write ports and two
        read ports that is arbited with a simple
        priority encoder.
        """

        # instantiate memory

        # publicly visible
        self.addr_shape = 24
        self.data_shape = 32

        self.read_port1 = ReadPort(self.addr_shape, self.data_shape, 'read_port1')
        self.write_port1 = WritePort(self.addr_shape, self.data_shape, 'write_port1')

        self.read_port2 = ReadPort(self.addr_shape, self.data_shape, 'read_port2')
        self.write_port2 = WritePort(self.addr_shape, self.data_shape, 'write_port2')
    
    def elaborate(self, platform):
        self.m = m = Module()

        m.submodules.mem = mem = sdram_controller()
        self.mem = mem

        # TODO : replace
        m.d.comb += self.read_port1.data.eq(mem.data_out)
        m.d.comb += self.read_port2.data.eq(mem.data_out)

        read_complete = Signal()
        write_complete = Signal()

        # TODO : replace
        m.d.sync += read_complete.eq(mem.data_valid)
        m.d.sync += write_complete.eq(mem.write_complete)

        self.address_comb = Signal(self.addr_shape)
        self.address_sync = Signal(self.addr_shape)
        self.data_comb = Signal(self.data_shape)
        self.data_sync = Signal(self.data_shape)

        # TODO : replace
        m.d.comb += mem.address.eq(self.address_comb | self.address_sync)
        m.d.comb += mem.data_in.eq(self.data_comb | self.data_sync)

        with m.FSM(name="Mem_FSM"):
            with m.State("IDLE"):
                with m.If(self.read_port1.rq):
                    m.d.comb += self.do_read(self.read_port1)
                    m.next = "SERVICING_PORT1_READ"
                
                with m.Elif(self.read_port2.rq):
                    m.d.comb += self.do_read(self.read_port2)
                    m.next = "SERVICING_PORT2_READ"
                
                with m.Elif(self.write_port1.rq):
                    m.d.comb += self.do_write(self.write_port1)
                    m.next = "SERVICING_PORT1_WRITE"

                with m.Elif(self.write_port2.rq):
                    m.d.comb += self.do_write(self.write_port2)
                    m.next = "SERVICING_PORT2_WRITE"
            
            with m.State("SERVICING_PORT1_READ"):
                with m.If(read_complete):
                    m.d.comb += self.read_port1.valid.eq(1)
                    self.reset_address_and_data()
                    m.next = "IDLE"

            with m.State("SERVICING_PORT2_READ"):
                with m.If(read_complete):
                    m.d.comb += self.read_port2.valid.eq(1)
                    self.reset_address_and_data()
                    m.next = "IDLE"

            with m.State("SERVICING_PORT1_WRITE"):
                with m.If(write_complete):
                    m.d.comb += self.write_port1.ack.eq(1)
                    self.reset_address_and_data()
                    m.next = "IDLE"

            with m.State("SERVICING_PORT2_WRITE"):
                with m.If(write_complete):
                    m.d.comb += self.write_port2.ack.eq(1)
                    self.reset_address_and_data()
                    m.next = "IDLE"


        return m
    
    def do_read(self, read_port):
        comb = []
        comb += [read_port.rdy.eq(1)]
        comb += [self.mem.req_read.eq(1)]
        self.set_address_and_data(read_port.addr, 0)
        return comb

    def do_write(self, write_port):
        comb = []
        comb += [self.mem.req_write.eq(1)]
        comb += [write_port.rdy.eq(1)]
        self.set_address_and_data(write_port.addr, write_port.data)
        return comb
    
    def set_address_and_data(self, addr, data):
        m = self.m
        m.d.comb += self.address_comb.eq(addr)
        m.d.sync += self.address_sync.eq(addr)

        m.d.comb += self.data_comb.eq(data)
        m.d.sync += self.data_sync.eq(data)

    def reset_address_and_data(self):
        m = self.m
        m.d.comb += self.address_comb.eq(0)
        m.d.sync += self.address_sync.eq(0)

        m.d.comb += self.data_comb.eq(0)
        m.d.sync += self.data_sync.eq(0)