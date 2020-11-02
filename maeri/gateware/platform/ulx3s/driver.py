from nmigen import Signal, Instance, Elaboratable
from nmigen import Module, ClockSignal, ResetSignal
from nmigen import Cat
from sdram_controller import sdram_controller
from ulx3s85f import ULX3SDomainGenerator

class driver(Elaboratable):

    def elaborate(self, platform):
        m = Module()
        m.submodules.domains = ULX3SDomainGenerator()

        with open(f"driver.v") as f:
            platform.add_file("driver.v", f.read())
        
        led = [platform.request("led",count, dir="-") for count in range(8)]
        m.submodules.mem = mem = sdram_controller()
        
        m.submodules += Instance("driver",
            i_clk = ClockSignal("compute"),
            i_rst = ResetSignal("compute"),
            i_button = platform.request("button_fire", 1, dir="-"),
            i_data_out = mem.data_out,
            i_data_valid = mem.data_valid,
            i_write_complete = mem.write_complete,

            o_address = mem.address,
            o_req_read = mem.req_read,
            o_req_write = mem.req_write,
            o_data_in = mem.data_in,
            o_led = Cat([light for light in led])
            )

        return m

if __name__ == "__main__":
    from nmigen_boards.ulx3s import ULX3S_85F_Platform
    top = driver()
    platform = ULX3S_85F_Platform()
    platform.build(top, do_program=True)