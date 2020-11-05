from maeri.common.enums import ConfigUp
from nmigen import Record
from nmigen.hdl.rec import Direction

class ConfigBus(Record):
    def __init__(self, name, INPUT_WIDTH):
        super().__init__([
            ('en',              1),
            ('addr',  INPUT_WIDTH),
            ('data',  INPUT_WIDTH),
            ('set_weight',      1),
        ], name=name)
    
    def connect(lhs, rhs):
        """
        example: m.d.comb += ldst.connect(mem.rp)
        """
        return [
            lhs.en            .eq(rhs.en),
            lhs.data          .eq(rhs.data),
            lhs.addr          .eq(rhs.addr),
            lhs.set_weight    .eq(rhs.set_weight),
        ]
