from nmigen import Elaboratable, Module
from nmigen import Signal, Array
from math import log2

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort
from maeri.common.helpers import prefix_record_name

class MemAdaptor(Elaboratable):
    def __init__(self, bytes_in_line, addr_shape, data_shape):
        """
        The MemAdaptor allows the compute unit to access memory with a
        percieve byte level granularity.
        """
        log2_bytes_in_mem_line = int(log2(bytes_in_line))
        self.bytes_in_line = bytes_in_line
        # signals facing memory
        self.read_port = ReadPort(addr_shape, data_shape, 'read_port')
        self.write_port = WritePort(addr_shape, data_shape, 'write_port')
        prefix_record_name(self.read_port, 'mem_adaptor')
        prefix_record_name(self.write_port, 'mem_adaptor')

        # signals facing compute unit
        self.mem_data = Array([Signal(8,name=f"mem_byte_{_}") for _ in range(bytes_in_line)])
        self.mem_addr = Signal(addr_shape + log2_bytes_in_mem_line)
        self.mem_line_addr = self.mem_addr[log2_bytes_in_mem_line:]
        self.mem_line_byte_select = self.mem_addr[:log2_bytes_in_mem_line]
        self.read_byte_ready = Signal(reset=1)
        self.read_rq = Signal()
    
    def elaborate(self, platform):
        m = Module()

        # alias ports for rapid access
        mem_data = self.mem_data
        read_rq = self.read_rq
        read_port = self.read_port
        mem_addr = self.mem_addr
        mem_line_addr = self.mem_line_addr
        mem_line_byte_select = self.mem_line_byte_select
        read_byte_ready = self.read_byte_ready

        # internal signals
        continue_read = Signal()
        addr_hold = Signal.like(mem_line_addr)
        # TODO : remove unecessary rename
        last_addr = addr_hold

        # mem read machinery
        with m.If(read_rq | continue_read):
            condition_1 = (mem_line_byte_select == 0)
            condition_2 = (last_addr != mem_line_addr)
            with m.If(condition_1 | condition_2 | continue_read):
                with m.FSM(name="MEM_READ"):
                    with m.State("BEGIN_READ"):
                        m.d.sync += continue_read.eq(1)
                        m.d.comb += read_byte_ready.eq(0)
                        m.d.comb += self.read_port.rq.eq(1)
                        m.d.comb += self.read_port.addr.eq(mem_line_addr)
                        m.d.sync += addr_hold.eq(mem_line_addr)
                        with m.If(self.read_port.rdy):
                            m.next = "FINISH_READ"
                
                    with m.State("FINISH_READ"):
                        m.d.comb += self.read_port.addr.eq(addr_hold)
                        with m.If(self.read_port.valid):
                            m.d.sync += continue_read.eq(0)
                            m.d.comb += mem_data[0].eq(self.read_port.data[0 : 8])
                            for byte in range(1, self.bytes_in_line):
                                m.d.sync += mem_data[byte].eq(
                                    self.read_port.data[byte*8 : (byte + 1)*8]
                                    )
                            m.next = "BEGIN_READ"
                        with m.Else():
                            m.d.comb += read_byte_ready.eq(0)

        return m