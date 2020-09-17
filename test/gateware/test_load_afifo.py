from nmigen import Elaboratable, Module
from nmigen import DomainRenamer

from maeri.platform.tinyfpgabx.load_afifo import LoadAfifo
from maeri.platform.tinyfpgabx.mem import Mem
from maeri.common.helpers import print_sig
from maeri.common.domains import comm_domain, compute_domain
from maeri.common.domains import compute_period, compute_period
from maeri.common.config import engine

import unittest
DEBUG = False

class TestLoadAfifo(Elaboratable):
    def __init__(self):
        # instantiate submodules
        self.mem = mem = Mem(width=32, depth=32, sim_init=True)
        self.load_afifo =\
            LoadAfifo(mem.addr_shape, mem.data_shape, 64,
            comm_domain=comm_domain, compute_domain=compute_domain)

    def elaborate(self, platform):
        m = Module()

        # attach submodules
        m.submodules.load_afifo = load_afifo = self.load_afifo
        m.submodules.mem = mem = DomainRenamer(compute_domain)(self.mem)

        m.d.comb += load_afifo.mem_domain_rp.connect(mem.read_port2)

        return m

from nmigen.sim import Simulator, Tick, Settle
dut = TestLoadAfifo()
sim = Simulator(dut, engine=engine)
sim.add_clock(comm_period, domain=comm_domain)
sim.add_clock(compute_period, domain=compute_domain)

answer = []
solution = []

class TestLoad(unittest.TestCase):
    def test_AsyncReadPortLink(self):
        # some aliases
        r_en = dut.load_afifo.comm_domain_rp.en
        data = dut.load_afifo.comm_domain_rp.data
        valid = dut.load_afifo.comm_domain_rp.valid

        rq1 = dut.mem.read_port1.rq

        def process():
            global answer
            global solution

            # requests to readport2 should be droppd
            # readport1 has priority and is actively
            # making requests
            yield rq1.eq(1)

            # requests some adresses
            yield  dut.load_afifo.comm_domain_rp.rq.eq(1)
            for tick in range(5):
                yield  dut.load_afifo.comm_domain_rp.addr.eq(tick)
                yield Tick(comm_domain)
                solution += [True]

            # allow readport2 requests to be treated
            yield rq1.eq(0)

            # disable adress requests and see what returns
            yield  dut.load_afifo.comm_domain_rp.rq.eq(0)

            for tick in range(1,6):
                while(not (yield valid)):
                    # and to spice things up...
                    # tests should still pass
                    yield rq1.eq((yield ~rq1))

                    yield Tick(comm_domain)

                yield r_en.eq(1)
                yield Settle()

                
                if DEBUG:
                    print(f"TICK = {tick}")
                    yield from print_sig(data)
                    yield from print_sig(valid)

                answer += [(yield data) == tick]
                yield Tick(comm_domain)

        sim.add_process(process)
        sim.run_until(comm_period*20)
        assert answer == solution


if __name__ == "__main__":
    DEBUG = True
    with sim.write_vcd(f"{__file__[:-3]}.vcd"):
        unittest.main()