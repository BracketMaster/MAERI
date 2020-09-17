from nmigen import Elaboratable, Signal, Module
from nmigen import Record

class PacketUpload(Record):
    def __init__(self, addr_shape, max_packet_size, name):
        super().__init__([
            ('ptr',                    addr_shape),
            ('upload',                           1),
            ('len',         range(max_packet_size + 1)),
            ('finished',                         1),
        ], name=name)
    
    def connect(lhs, rhs):
        return [
            lhs.ptr                 .eq(rhs.ptr),
            lhs.upload              .eq(rhs.upload),
            lhs.len                 .eq(rhs.len),
            rhs.finished            .eq(lhs.finished),
        ]

class PacketDownload(Record):
    def __init__(self, addr_shape, max_packet_size, name):
        super().__init__([
            ('ptr',                    addr_shape),
            ('download',                         1),
            ('finished',                         1),
        ], name=name)
    
    def connect(lhs, rhs):
        return [
            lhs.ptr                 .eq(rhs.ptr),
            lhs.download            .eq(rhs.download),
            rhs.finished            .eq(lhs.finished),
        ]

class WritePort(Record):
    def __init__(self, addr_shape, data_shape, name):
        super().__init__([
            ('en',               1),
            ('ack',              1),
            ('addr',    addr_shape),
            ('data',    data_shape),
            ('rq',               1),
            ('rdy',              1)
        ], name=name)
    
    def connect(lhs, rhs):
        """
        example: m.d.comb += mem.wp.connect(ldst.wp)
        """
        return [
            lhs.en      .eq(rhs.en),
            lhs.addr    .eq(rhs.addr),
            lhs.data    .eq(rhs.data),
            lhs.rq      .eq(rhs.rq),
            rhs.rdy     .eq(lhs.rdy),
            rhs.ack     .eq(lhs.ack)
        ]

class ReadPort(Record):
    def __init__(self, addr_shape, data_shape, name):
        super().__init__([
            ('addr',    addr_shape),
            ('data',    data_shape),
            ('rq',               1),
            ('en',               1),
            ('rdy',              1),
            ('valid',            1)
        ], name=name)
    
    def connect(lhs, rhs):
        """
        example: m.d.comb += ldst.connect(mem.rp)
        """
        return [
            rhs.addr    .eq(lhs.addr),
            lhs.data    .eq(rhs.data),
            lhs.rdy     .eq(rhs.rdy),
            lhs.valid     .eq(rhs.valid),
            rhs.rq      .eq(lhs.rq),
            rhs.en      .eq(lhs.en)
        ]