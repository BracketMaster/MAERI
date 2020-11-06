from nmigen import Elaboratable, Signal, Module
from nmigen import Array

from luna.gateware.stream import StreamInterface
from maeri.gateware.platform.shared.interfaces import PacketUpload, ReadPort

from maeri.common.helpers import prefix_record_name

class Load(Elaboratable):
    def __init__(self, addr_shape, data_shape, max_packet_size):
        # verifications
        if (data_shape % 8) != 0:
            raise ValueError(f"MEMORY WIDTH {data_shape} IS NOT " +  
                "DIVISIBLE BY 8.")

        # serial link signals
        self.tx = StreamInterface()
        prefix_record_name(self.tx, 'load_tx_link')

        # memory signals
        self.rp = ReadPort(addr_shape, data_shape, name='rp')

        # interface controller signals
        self.control = PacketUpload(addr_shape, max_packet_size, name='control')

        # params
        self.addr_shape = addr_shape
        self.data_shape = data_shape
        self.max_packet_size = max_packet_size
    
    def elaborate(self, platform):
        self.m = m = Module()

        # aliases
        tx = self.tx
        rp = self.rp
        control = self.control

        # memory line can have multiple bytes
        # serial link payloads are one byte each
        bytes_in_line = int(self.data_shape/8)
        byte_select = Signal(range(bytes_in_line))
        mem_line = \
            Array([Signal(8, name=f"mem_line{_}") for _ in range(bytes_in_line)])

        offset = Signal.like(control.ptr)
        payload_count = Signal(range(64))

        with m.FSM():
            with m.State('IDLE'):

                with m.If(control.upload):
                    m.d.sync += offset.eq(0)
                    m.d.sync += payload_count.eq(0)
                    m.next = 'UPLOAD'
            
            with m.State('UPLOAD'):
                # payload comes from selected byte of mem line
                with m.If(byte_select == 0):
                    m.d.comb += tx.payload.eq(rp.data[0:8])
                with m.Else():
                    m.d.comb += tx.payload.eq(mem_line[byte_select])

                # check if transmission link is available
                with m.If(tx.ready):
                    with m.If(byte_select == 0):
                        with m.If(rp.valid):
                            for index, byte in enumerate(mem_line):
                                m.d.sync += byte.eq(rp.data[index*8: 8*(index + 1)])

                            m.d.comb += rp.en.eq(1)
                            m.d.comb += tx.valid.eq(1)
                            with m.If(payload_count == 0):
                                m.d.comb += tx.first.eq(1)
                            with m.If(bytes_in_line != 1):
                                m.d.sync += byte_select.eq(byte_select + 1)
                    with m.Else():
                        m.d.comb += tx.valid.eq(1)
                        with m.If(byte_select == (bytes_in_line - 1)):
                            m.d.sync += byte_select.eq(0)
                        with m.Else():
                            m.d.sync += byte_select.eq(byte_select + 1)

                # start pushing read requests onto AFIFO
                with m.If(offset < control.len):
                    with m.If(rp.rdy):
                        m.d.sync += offset.eq(offset + 1)
                        m.d.comb += rp.rq.eq(1)
                        m.d.comb += rp.addr.eq(control.ptr + offset)
                
                with m.If(tx.valid):
                    m.d.sync += payload_count.eq(payload_count + 1)
                
                    with m.If(payload_count == (self.max_packet_size - 1)):
                        m.d.comb += control.finished.eq(1)
                        m.d.comb += tx.last.eq(1)
                        m.next = 'IDLE'

        return m