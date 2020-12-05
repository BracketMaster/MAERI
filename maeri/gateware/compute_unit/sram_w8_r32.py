from nmigen import Memory
from nmigen import Signal, Module, Elaboratable
from nmigen.sim import Simulator, Tick, Settle

class Sram_w8_r32(Elaboratable):
    """
    Creates a synchronous SRAM 16 deep wth the following attributes:
     - write adress signal is 6 bits wide
     - write port data is 8 bits wide
     - read port address signal is 4 bits wide 
     - read port data is 8 32 wide
    """
    def __init__(self):
        self.rp_data = Signal(32)
        self.rp_addr = Signal(4)
        self.rp_en = Signal()

        self.wp_data = Signal(8)
        self.wp_addr = Signal(6)
        self.wp_en = Signal()
    
    def elaborate(self, platform):
        mem = Memory(width=32, depth=16, attrs={'ram_block' : 1})
        read_port = mem.read_port(transparent=False)
        write_port = mem.write_port(granularity=8)
        m = Module()
        m.submodules.rp = read_port
        m.submodules.wp = write_port

        # attach
        m.d.comb += read_port.addr.eq(self.rp_addr)
        m.d.comb += read_port.en.eq(self.rp_en)
        m.d.comb += self.rp_data.eq(read_port.data)

        m.d.comb += write_port.addr.eq(self.wp_addr[2:])
        with m.If(self.wp_en):
            m.d.comb += write_port.en.eq(1 << self.wp_addr[:2])
            m.d.comb += write_port.data.eq(self.wp_data << (self.wp_addr[:2] * 8))
        with m.Else():
            m.d.comb += write_port.en.eq(0)
        

        return m

if __name__ == "__main__":
    dut = Sram_w8_r32()

def process():
    yield dut.wp_en.eq(1)
    for addr, val in enumerate([0xEF, 0xBE, 0xAD, 0xDE]):
    #for addr, val in enumerate([0x01, 0x23, 0x45, 0x67]):
        yield dut.wp_addr.eq(addr)
        yield dut.wp_data.eq(val)
        yield Tick()

    yield dut.wp_en.eq(0)
    yield dut.rp_en.eq(1)
    yield dut.rp_addr.eq(0)
    yield Tick()
    yield Settle()

    print(f"{(yield dut.rp_data):02x}")

if __name__ == "__main__":
    sim = Simulator(dut, engine="pysim")
    sim.add_clock(1e-6)
    sim.add_process(process)

    with sim.write_vcd(f"{__file__[:-3]}.vcd"):
        sim.run()