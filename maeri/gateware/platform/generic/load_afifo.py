from nmigen import  Memory, Signal, Module
from nmigen import Record, Elaboratable, Cat
from nmigen.lib.fifo import AsyncFIFOBuffered
from maeri.gateware.platform.generic.interfaces import ReadPort

class LoadAfifo(Elaboratable):
    def __init__(self, addr_shape, data_shape, max_packet_size, comm_domain, compute_domain):
        # read_port to connect to memory
        self.comm_domain_rp = ReadPort(addr_shape, data_shape, 'comm_domain_rp')
        self.mem_domain_rp = ReadPort(addr_shape, data_shape, 'mem_domain_rp')

        # parameters
        self.depth = max_packet_size + 1
        self.addr_shape = addr_shape
        self.data_shape = data_shape
        self.comm_domain = comm_domain
        self.compute_domain = compute_domain
    
    def elaborate(self, platform):
        m = Module()

        comm_domain_rp = self.comm_domain_rp
        mem_domain_rp = self.mem_domain_rp

        # async FIFO for crossing from load to memory
        # clock domain
        m.submodules.load_to_mem_afifo = load_to_mem_afifo \
            = AsyncFIFOBuffered(
                width=comm_domain_rp.addr.shape().width, depth=self.depth,
                w_domain=self.comm_domain, r_domain=self.compute_domain
            )

        # pass request from load unit's clock domain to
        # memory's clock domain
        m.d.comb += load_to_mem_afifo.w_data.eq(comm_domain_rp.addr)
        m.d.comb += comm_domain_rp.rdy.eq(load_to_mem_afifo.w_rdy)
        with m.If(comm_domain_rp.rq):
            m.d.comb += load_to_mem_afifo.w_en.eq(1)

        # allow memory to see requests in its clock domain
        with m.If(load_to_mem_afifo.r_rdy):
            m.d.comb += mem_domain_rp.rq.eq(1)
            with m.If(mem_domain_rp.rdy):
                m.d.comb += load_to_mem_afifo.r_en.eq(1)
                m.d.comb += mem_domain_rp.addr.eq(load_to_mem_afifo.r_data)
        

        # async FIFO for crossing from memory to load
        # clock domain
        m.submodules.mem_to_load_afifo = mem_to_load_afifo \
            = AsyncFIFOBuffered(
            width=mem_domain_rp.data.shape().width,
            depth=self.depth, w_domain=self.compute_domain, r_domain=self.comm_domain
            )

        # pass data from mem's clock domain to load unit's
        # clock domain
        m.d.comb += mem_to_load_afifo.w_data.eq(mem_domain_rp.data)
        with m.If(mem_domain_rp.valid & mem_to_load_afifo.w_rdy):
            m.d.comb += mem_to_load_afifo.w_en.eq(1)
        
        # allow load unit to see results in its domain
        with m.If(mem_to_load_afifo.r_rdy & comm_domain_rp.en):
            m.d.comb += mem_to_load_afifo.r_en.eq(1)
            m.d.comb += comm_domain_rp.data.eq(mem_to_load_afifo.r_data)
        m.d.comb += comm_domain_rp.valid.eq(mem_to_load_afifo.r_rdy)
        
        return m