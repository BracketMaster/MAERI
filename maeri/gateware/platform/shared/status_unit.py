from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable, Cat
from nmigen.lib.fifo import AsyncFIFOBuffered

from maeri.gateware.compute_unit.top import State

class StatusUnit(Elaboratable):
    def __init__(self, comm_domain, compute_domain):
        # read by MAERI controller
        self.read_start_command = Signal()
        # read by interface controller
        self.read_compute_status = Signal(State)

        # written by interface controller
        self.write_start_command = Signal()
        # written by MAERI controller
        self.write_compute_status = Signal(State)

        # parameters
        self.comm_domain = comm_domain
        self.compute_domain = compute_domain
    
    def elaborate(self, platform):
        m = Module()

        # async FIFO for crossing from communication domain to compute domain
        m.submodules.load_to_maeri_afifo = load_to_maeri_afifo \
            = AsyncFIFOBuffered(width=self.write_start_command.width, depth=3, 
                        w_domain=self.comm_domain, r_domain=self.compute_domain)
        m.d.comb += load_to_maeri_afifo.w_en.eq(load_to_maeri_afifo.w_rdy)
        m.d.comb += load_to_maeri_afifo.r_en.eq(load_to_maeri_afifo.r_rdy)
        m.d.comb += load_to_maeri_afifo.w_data.eq(self.write_start_command)
        m.d.comb += self.read_start_command.eq(load_to_maeri_afifo.r_data)

        # async FIFO for crossing from compute domain to communication domain
        m.submodules.maeri_to_load_afifo = maeri_to_load_afifo \
            = AsyncFIFOBuffered(width=self.write_compute_status.width, depth=3,
                        w_domain=self.compute_domain, r_domain=self.comm_domain)
        m.d.comb += maeri_to_load_afifo.w_en.eq(maeri_to_load_afifo.w_rdy)
        m.d.comb += maeri_to_load_afifo.r_en.eq(maeri_to_load_afifo.r_rdy)
        m.d.comb += maeri_to_load_afifo.w_data.eq(self.write_compute_status)
        m.d.comb += self.read_compute_status.eq(maeri_to_load_afifo.r_data)

        return m