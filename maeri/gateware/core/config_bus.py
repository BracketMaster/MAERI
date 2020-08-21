from maeri.common.enums import ConfigUp
from nmigen import Record
from nmigen.hdl.rec import Direction

def config_bus(name, INPUT_WIDTH):
    config_bus = [
        ("En", 1),
        ("Addr", 8),
        ("Data", INPUT_WIDTH),
        ("Inject_En", 1)
        ]
    return Record(config_bus, name = name)