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

        # read port data always available one cycle 
        # after read request
        m.d.sync += self.read_port1.valid.eq(self.read_port1.rdy)
        m.d.sync += self.read_port2.valid.eq(self.read_port2.rdy)

        # acknowledge that write has occured
        m.d.comb += self.write_port1.ack.eq(self.write_port1.rdy)
        m.d.comb += self.write_port2.ack.eq(self.write_port2.rdy)
        
        with m.If(self.read_port1.rq):
            self.do_read(self.read_port1)
        with m.Elif(self.read_port2.rq):
            self.do_read(self.read_port2)

        with m.If(self.write_port1.rq):
            self.do_write(self.write_port1)
        with m.Elif(self.write_port2.rq):
            self.do_write(self.write_port2)

        return m
    
    def do_read(self, read_port):
        m = self.m
        rp = self.__rp
        m.d.comb += read_port.rdy.eq(1)
        m.d.comb += rp.addr.eq(read_port.addr)

    def do_write(self, write_port):
        m = self.m
        wp = self.__wp
        m.d.comb += write_port.rdy.eq(1)
        m.d.comb += wp.en.eq(write_port.en)
        m.d.comb += wp.addr.eq(write_port.addr)
        m.d.comb += wp.data.eq(write_port.data)

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