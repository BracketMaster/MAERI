from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable
from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort

class Mem(Elaboratable):
    def __init__(self, width, depth, sim_init=False):
        """
        A memory with two write ports and two
        read ports that is arbited with a simple
        priority encoder.
        """
        init = None
        if sim_init:
            from random import randint
            init = [val for val in range(1, depth + 1)]
        
        if width < 16:
            raise ValueError("MEMORY WIDTH MUST BE AT LEAST 16 BITS")

        mem = Memory(width=width, depth=depth, init=init)
        mem.attrs['ram_block'] = 1
        self.__rp = mem.read_port()
        self.__wp = mem.write_port()

        # publicly visible
        self.addr_shape = self.__wp.addr.shape().width
        print(f"addr_shape = {self.addr_shape}")
        self.data_shape = self.__wp.data.shape().width

        self.read_port1 = ReadPort(self.addr_shape, self.data_shape, 'read_port1')
        self.write_port1 = WritePort(self.addr_shape, self.data_shape, 'write_port1')

        self.read_port2 = ReadPort(self.addr_shape, self.data_shape, 'read_port2')
        self.write_port2 = WritePort(self.addr_shape, self.data_shape, 'write_port2')
    
    def elaborate(self, platform):
        self.m = m = Module()
        m.submodules.rp = rp = self.__rp
        m.submodules.wp = wp = self.__wp

        # TODO : replace
        m.d.comb += self.read_port1.data.eq(self.__rp.data)
        m.d.comb += self.read_port2.data.eq(self.__rp.data)

        read_complete = Signal()
        write_complete = Signal()

        # TODO : replace
        m.d.sync += read_complete.eq(self.read_port1.rdy | self.read_port2.rdy)
        m.d.sync += write_complete.eq(self.write_port1.rdy | self.write_port2.rdy)

        self.address_comb = Signal(self.addr_shape)
        self.address_sync = Signal(self.addr_shape)
        self.data_comb = Signal(self.data_shape)
        self.data_sync = Signal(self.data_shape)

        # TODO : replace
        m.d.comb += self.__rp.addr.eq(self.address_comb | self.address_sync)
        m.d.comb += self.__wp.addr.eq(self.address_comb | self.address_sync)

        m.d.comb += self.__wp.data.eq(self.data_comb | self.data_sync)

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
        # TODO : insert mem request
        comb += [read_port.rdy.eq(1)]
        self.set_address_and_data(read_port.addr, 0)
        return comb

    def do_write(self, write_port):
        wp = self.__wp
        comb = []
        comb += [write_port.rdy.eq(1)]
        comb += [wp.en.eq(write_port.en)]
        # TODO : insert mem request
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