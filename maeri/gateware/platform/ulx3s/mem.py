from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable
from maeri.gateware.platform.generic.interfaces import WritePort, ReadPort

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
        self.data_shape = self.__wp.data.shape().width

        self.read_port1 = ReadPort(self.addr_shape, self.data_shape, 'read_port1')
        self.write_port1 = WritePort(self.addr_shape, self.data_shape, 'write_port1')

        self.read_port2 = ReadPort(self.addr_shape, self.data_shape, 'read_port2')
        self.write_port2 = WritePort(self.addr_shape, self.data_shape, 'write_port2')
    
    def elaborate(self, platform):
        self.m = m = Module()
        m.submodules.rp = rp = self.__rp
        m.submodules.wp = wp = self.__wp

        # read port data is always connected
        m.d.comb += self.read_port1.data.eq(self.__rp.data)
        m.d.comb += self.read_port2.data.eq(self.__rp.data)

        read_condition = (self.read_port1.rdy | self.read_port2.rdy)
        write_condition = (self.write_port1.rdy | self.write_port2.rdy)

        read_complete = Signal()
        write_complete = Signal()

        m.d.sync += read_complete.eq(read_condition)
        m.d.comb += write_complete.eq(write_condition)

        with m.FSM(name="Mem_FSM"):
            with m.State("IDLE"):
                with m.If(self.read_port1.rq):
                    m.d.comb += self.do_read(self.read_port1)
                    with m.If(read_complete):
                        m.d.comb += self.read_port1.valid.eq(1)
                    with m.Else():
                        m.next = "SERVICING_PORT1_READ"
                
                with m.Elif(self.read_port2.rq):
                    m.d.comb += self.do_read(self.read_port2)
                    with m.If(read_complete):
                        m.d.comb += self.read_port2.valid.eq(1)
                    with m.Else():
                        m.next = "SERVICING_PORT2_READ"
                
                with m.Elif(self.write_port1.rq):
                    m.d.comb += self.do_write(self.write_port1)
                    with m.If(write_complete):
                        m.d.comb += self.write_port1.ack.eq(1)
                    with m.Else():
                        m.next = "SERVICING_PORT1_WRITE"

                with m.Elif(self.write_port2.rq):
                    m.d.comb += self.do_write(self.write_port2)
                    with m.If(write_complete):
                        m.d.comb += self.write_port2.ack.eq(1)
                    with m.Else():
                        m.next = "SERVICING_PORT2_WRITE"
            
            with m.State("SERVICING_PORT1_READ"):
                with m.If(read_complete):
                    m.d.comb += self.read_port1.valid.eq(1)
                    m.next = "IDLE"

            with m.State("SERVICING_PORT2_READ"):
                with m.If(read_complete):
                    m.d.comb += self.read_port2.valid.eq(1)
                    m.next = "IDLE"

            with m.State("SERVICING_PORT1_WRITE"):
                with m.If(write_complete):
                    m.d.comb += self.write_port1.ack.eq(1)
                    m.next = "IDLE"

            with m.State("SERVICING_PORT2_WRITE"):
                with m.If(write_complete):
                    m.d.comb += self.write_port2.ack.eq(1)
                    m.next = "IDLE"


        return m
    
    def do_read(self, read_port):
        rp = self.__rp
        comb = []
        comb += [read_port.rdy.eq(1)]
        comb += [rp.addr.eq(read_port.addr)]
        return comb

    def do_write(self, write_port):
        wp = self.__wp
        comb = []
        comb += [write_port.rdy.eq(1)]
        comb += [wp.en.eq(write_port.en)]
        comb += [wp.addr.eq(write_port.addr)]
        comb += [wp.data.eq(write_port.data)]
        return comb

if __name__ == '__main__':
    from nmigen.sim import Simulator
    def process():
        for tick in range(4):
            yield
    
    dut = Mem(width=16, depth=32, sim_init=True)
    sim = Simulator(dut)
    sim.add_clock(1e-6)
    sim.add_sync_process(process)

    with sim.write_vcd(f"{__file__[:-3]}.vcd"):
        sim.run()