from nmigen import Memory, Array, Cat
from nmigen import Signal, Module, Elaboratable
from nmigen.sim import Simulator, Tick, Settle

class Sram_w32_r8(Elaboratable):
    """
    Creates a synchronous SRAM 16 deep wth the following attributes:
     - write adress signal is 4 bits wide
     - write port data is 32 bits wide
     - read port address signal is 6 bits wide 
     - read port data is 8 bits wide
    """
    def __init__(self):
        self.rp_data = Signal(8)
        self.rp_addr = Signal(6)
        self.rp_en = Signal()

        self.wp_data = Signal(32)
        self.wp_addr = Signal(4)
        self.wp_en = Signal()
    
    def elaborate(self, platform):
        m = Module()
        list_of_read_ports = []
        list_of_write_ports = []
        for index in range(4):
            mem = Memory(width=8, depth=16, attrs={'ram_block' : 1})
            rp = mem.read_port(transparent=False)
            wp = mem.write_port()
            list_of_read_ports += [rp]
            list_of_write_ports += [wp]
            setattr(m.submodules, f"sub_rp_{index}", rp)
            setattr(m.submodules, f"sub_wp_{index}", wp)
        
        m.d.comb += Cat([port.data for port in list_of_write_ports]).eq(self.wp_data)
        m.d.comb += [port.addr.eq(self.wp_addr) for port in list_of_write_ports]
        m.d.comb += [port.en.eq(self.wp_en) for port in list_of_write_ports]

        m.d.comb += [port.addr.eq(self.rp_addr[2:]) for port in list_of_read_ports]
        m.d.comb += self.rp_data\
            .eq(Array([port.data for port in list_of_read_ports])[self.rp_addr[:2]])
        m.d.comb += [port.en.eq(self.rp_en) for port in list_of_read_ports]

        return m

if __name__ == "__main__":
    dut = Sram_w32_r8()

def process():
    yield dut.wp_en.eq(1)
    yield dut.wp_addr.eq(0)
    yield dut.wp_data.eq(0xDEADBEEF)
    yield Tick()

    yield dut.wp_en.eq(1)
    yield dut.wp_addr.eq(1)
    yield dut.wp_data.eq(0xFACEB00C)
    yield Tick()

    yield dut.wp_en.eq(0)
    yield dut.rp_en.eq(1)

    for addr in range(8):
        yield dut.rp_addr.eq(addr)
        yield Tick()
        yield Settle()

        print(f"{(yield dut.rp_data):02x}")

if __name__ == "__main__":
    sim = Simulator(dut, engine="pysim")
    sim.add_clock(1e-6)
    sim.add_process(process)

    with sim.write_vcd(f"{__file__[:-3]}.vcd"):
        sim.run()