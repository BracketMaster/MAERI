from nmigen import Signal, Module, Elaboratable
from nmigen import Record, Array

from maeri.gateware.platform.shared.interfaces import WritePort, ReadPort

from luna.gateware.stream import StreamInterface
from maeri.gateware.platform.shared.interfaces import PacketDownload

from maeri.common.helpers import prefix_record_name

class Store(Elaboratable):
    """
     - download packets from  the serial link
    to memory
    """

    def __init__(self, addr_shape, data_shape, max_packet_size):
        # serial link signals
        self.rx = StreamInterface()
        prefix_record_name(self.rx, 'store_rx_link')

        # memory signals
        self.wp = WritePort(addr_shape, data_shape, 'write_port')

        # interface controller signals
        self.control = PacketDownload(addr_shape, max_packet_size, 'control')

        # parameters
        self.max_packet_size = max_packet_size
        self.data_shape = data_shape
    
    def elaborate(self, platform):
        self.m = m = Module()
        control = self.control
        offset = Signal.like(control.ptr)
        ack_count = Signal(range(self.max_packet_size))
        writes_sent = Signal()

        # memory line can have multiple bytes
        # serial link payloads are one byte each

        self.bytes_in_line = bytes_in_line = int(self.data_shape/8)
        byte_select = Signal(range(bytes_in_line))
        mem_line =\
            Array([Signal(8,name = f"mem_line{_}") for _ in range(bytes_in_line - 1)])

        with m.FSM(name='IDLE/DOWNLOAD'):
            with m.State('IDLE'):

                with m.If(control.download):
                    m.d.sync += offset.eq(0)
                    m.next = 'DOWNLOAD'
                    m.d.sync += ack_count.eq(0)
                    m.d.sync += writes_sent.eq(0)

                    m.d.sync += byte_select.eq(0)
            
            with m.State('DOWNLOAD'):
                m.d.comb += self.wp.rq.eq(1)
                m.d.comb += self.rx.ready.eq(self.wp.rdy)

                with m.FSM(name="store/done"):
                    with m.State('STORE'):
                        with m.If(self.rx.valid & self.wp.rdy):
                            m.d.sync += byte_select.eq(byte_select + 1)

                            with m.If(byte_select == (bytes_in_line - 1)):
                                m.d.sync += byte_select.eq(0)
                                self.store_data(control.ptr + offset, mem_line, self.rx.payload)
                                self.increment(offset)
                            with m.Else():
                                m.d.sync += mem_line[byte_select].eq(self.rx.payload)

                            with m.If(self.rx.last):
                                m.next = 'DONE'
                            with m.Else():
                                m.next = 'STORE'

                    with m.State('DONE'):
                        m.d.sync += writes_sent.eq(1)
                        m.d.comb += self.rx.ready.eq(0)

                        with m.If(writes_sent & (ack_count == offset)):
                            m.next = 'STORE'

                with m.If(self.wp.ack):
                    m.d.sync += ack_count.eq(ack_count + 1)
                
                with m.If(writes_sent & (ack_count == offset)):
                    m.d.comb += control.finished.eq(1)
                    m.next = 'IDLE'

        return m
    
    def store_data(self, addr, mem_line, rx_payload):
        m = self.m
        m.d.comb += self.wp.en.eq(1)
        m.d.comb += self.wp.addr.eq(addr)

        if self.bytes_in_line > 1:
            for index, signal in enumerate(mem_line):
                m.d.comb += self.wp.data[index*8: 8*(index + 1)].eq(signal)

        index = self.bytes_in_line - 1
        m.d.comb += self.wp.data[index*8: 8*(index + 1)].eq(rx_payload)
    
    def increment(self, offset):
        self.m.d.sync += offset.eq(offset + 1)