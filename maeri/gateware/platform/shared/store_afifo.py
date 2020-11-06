from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable, Cat
from nmigen.lib.fifo import AsyncFIFOBuffered

from maeri.gateware.platform.shared.interfaces import WritePort

class StoreAfifo(Elaboratable):
    def __init__(self, addr_shape, data_shape, max_packet_size, comm_domain, compute_domain):
        # memory ports
        self.comm_domain_wp = WritePort(addr_shape, data_shape, 'comm_domain_wp')
        self.compute_domain_wp = WritePort(addr_shape, data_shape, 'compute_domain_wp')

        # parameters
        self.depth = max_packet_size + 1
        self.comm_domain = comm_domain
        self.compute_domain = compute_domain
    
    def elaborate(self, platform):
        m = Module()

        comm_domain_wp = self.comm_domain_wp
        compute_domain_wp = self.compute_domain_wp

        data_store = Cat(comm_domain_wp.addr, comm_domain_wp.data)
        data_mem = Cat(compute_domain_wp.addr, compute_domain_wp.data)

        # fifo to pass write requests to memory
        m.submodules.store_to_mem_afifo = store_to_mem_afifo \
            = AsyncFIFOBuffered(
                width=data_mem.shape().width, depth=self.depth,
                w_domain=self.comm_domain, r_domain=self.compute_domain
            )

        m.d.comb += store_to_mem_afifo.w_data.eq(data_store)
        m.d.comb += comm_domain_wp.rdy.eq(store_to_mem_afifo.w_rdy)
        m.d.comb += store_to_mem_afifo.w_en.eq(comm_domain_wp.en)

        m.d.comb += data_mem.eq(store_to_mem_afifo.r_data)
        m.d.comb += compute_domain_wp.rq.eq(store_to_mem_afifo.r_rdy)
        m.d.comb += store_to_mem_afifo.r_en.eq(compute_domain_wp.rdy)
        m.d.comb += compute_domain_wp.en.eq(store_to_mem_afifo.r_rdy)

        # set up afifo for acknowledges
        m.submodules.mem_to_store_afifo = mem_to_store_afifo \
            = AsyncFIFOBuffered(
                width=compute_domain_wp.ack.shape().width, depth=self.depth,
                w_domain=self.compute_domain, r_domain=self.comm_domain
            )
        
        m.d.comb += mem_to_store_afifo.w_data.eq(compute_domain_wp.ack)
        m.d.comb += mem_to_store_afifo.w_en.eq(compute_domain_wp.ack)
        m.d.comb += mem_to_store_afifo.r_en.eq(mem_to_store_afifo.r_rdy)
        m.d.comb += \
            comm_domain_wp.ack.eq(mem_to_store_afifo.r_data & mem_to_store_afifo.r_rdy)

        return m