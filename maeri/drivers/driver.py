def Driver(platform):
    if platform == 'tinyfpga':
        from maeri.drivers.fpga_driver import FPGADriver
        return FPGADriver()
    from maeri.drivers.sim_driver import SimDriver
    return SimDriver()