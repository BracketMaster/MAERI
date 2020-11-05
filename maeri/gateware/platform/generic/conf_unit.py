from nmigen import Signal, Elaboratable, Module
from nmigen import signed

from maeri.gateware.core.config_bus import ConfigBus

class ConfUnit(Elaboratable):
    def __init__(self, bytes_in_line, addr_shape, mem_width, INPUT_WIDTH):
        self.INPUT_WIDTH = INPUT_WIDTH

        self.mem_line = Signal(mem_width)
        self.en = Signal()
        self.offset = Signal(INPUT_WIDTH)
        self.set_weiight = Signal()

        # create list of config ports
        self.config_ports_out = []
        for port in range(bytes_in_line):
            self.config_ports_out.append(ConfigBus(
                name = f"external_config_{port}",
                INPUT_WIDTH = INPUT_WIDTH))
    
    def elaborate(self, platform):
        m = Module()

        # connect up data on each config bus
        for index, port in enumerate(self.config_ports_out):
            sub_word = self.mem_line[index*self.INPUT_WIDTH : (index + 1)*self.INPUT_WIDTH]
            m.d.comb += port.data.eq(sub_word)
            m.d.comb += port.addr.eq(self.offset + index)
        
        for port in self.config_ports_out:
            port.en.eq(self.en)
            port.set_weight.eq(self.set_weiight)
        
        return m
    
    def ports(self):
        ports = []
        ports += [self.mem_line]
        ports += [self.en]
        ports += [self.offset]
        ports += [self.set_weiight]
        for port in self.config_ports_out:
            ports += [port[sig] for sig in port.fields]
        
        return ports

if __name__ == "__main__":
    top = ConfUnit(bytes_in_line=4, addr_shape=32, mem_width=32, INPUT_WIDTH=8)

    # generate verilog
    from nmigen.back import verilog
    name = __file__[:-3]
    f = open(f"{name}.v", "w")
    f.write(verilog.convert(top, 
        name = name,
        strip_internal_attrs=True,
        ports=top.ports())
    )
