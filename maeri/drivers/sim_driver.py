from nmigen import Module
from nmigen.sim import Simulator, Delay
from nmigen.sim import Settle, Tick
from maeri.common.config import engine, max_packet_size, vcd

from maeri.gateware.platform.sim.top import Top

from maeri.gateware.platform.sim.serial_model import inject_packet, recieve_packet

from maeri.common.domains import comm_domain, comm_period
from maeri.common.domains import compute_domain, compute_period

from json import loads


class SimDriver():
    def __init__(self):
        top = Top(max_packet_size=max_packet_size)
        dut = Module()
        dut.submodules.top = top
        self.top = top

        self.sim = sim = Simulator(dut, engine=engine)
        sim.add_clock(comm_period, domain=comm_domain)
        sim.add_clock(compute_period, domain=compute_domain)

        if vcd == 'on':
            self.write_object = self.sim.write_vcd(f"{__file__[:-3]}.vcd")
            self.write_object.__enter__()

        config = loads(self.get_config())
        print(f"device config = {config}")
        self.max_packet_size = config['b_in_packet']
        self.mem_width = config['b_in_line']
        self.mem_depth = config['m_depth']
        self.ports = config['ports']
        self.no_mults = config['no.mults']
        self.packets_in_mem = (self.mem_depth * self.mem_width)//self.max_packet_size
        self.mem_size = self.mem_depth * self.mem_width
    
    def start_compute(self):
        def send():
            yield from inject_packet(b"do_start", self.top.serial_link.rx)

        self.sim.add_process(send)
        self.sim.run()

    def get_config(self):
        
        def send():
            yield from inject_packet(b"r_config", self.top.serial_link.rx)

        self.sim.add_process(send)
        self.sim.run()

        self.length = None
        def get_length():
            self.length = (yield from self.recieve())[0]

        self.sim.add_process(get_length)
        self.sim.run()

        self.data = []
        def recieve():
            self.data += (yield from self.recieve())

        for packet in range(self.length):
            self.sim.add_process(recieve)
            self.sim.run()

        self.data = ''.join([chr(letter) for letter in self.data])

        return self.data

    def get_status(self):
        
        def send():
            yield from inject_packet(b"r_status", self.top.serial_link.rx)

        self.sim.add_process(send)
        self.sim.run()

        self.data = None
        def get_status():
            self.data = (yield from self.recieve())

        self.sim.add_process(get_status)
        self.sim.run()
        self.data = [int(el) for el in self.data]

        return self.data[0]
    
    def inject(self, data):
        yield from inject_packet(data, self.top.serial_link.rx, self.max_packet_size)
    
    def recieve(self):
        return (yield from recieve_packet(self.top.serial_link.tx))

    def write(self, start_adress, data):
        if (len(data) % self.max_packet_size):
            raise ValueError("DATA MUST BE MULTIPLE OF max_packet_size")


        def process():
            length = len(data) // self.max_packet_size
            yield from self.inject(b'download')
            yield from self.inject(int(start_adress).to_bytes(8, 'little'))
            yield from self.inject(int(length).to_bytes(8, 'little'))

            index = self.max_packet_size
            for count in range(length):
                yield from self.inject(data[count*index : (count + 1)*index])
        
        self.sim.add_process(process)
        self.sim.run()

    def read(self, start_adress, length):
        
        def send():
            yield from self.inject(b'upload')
            yield from self.inject(int(start_adress).to_bytes(8, 'little'))
            yield from self.inject(int(length).to_bytes(8, 'little'))

        self.sim.add_process(send)
        self.sim.run()

        self.data = []
        def recieve():
            self.data += (yield from self.recieve())

        for packet in range(length):
            self.sim.add_process(recieve)
            self.sim.run()

        return self.data
