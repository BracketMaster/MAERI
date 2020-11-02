def Driver(platform):
    if platform == 'ulx3s':
        from maeri.drivers.fpga_driver import FPGADriver
        return FPGADriver()
    from maeri.drivers.sim_driver import SimDriver
    return SimDriver()