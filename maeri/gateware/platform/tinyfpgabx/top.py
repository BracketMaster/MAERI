from nmigen import  Signal, Module, DomainRenamer
from nmigen import Record, Elaboratable

from luna.gateware.stream import StreamInterface

from maeri.gateware.platform.tinyfpgabx.mem import Mem
from maeri.gateware.platform.generic.store import Store
from maeri.gateware.platform.generic.load import Load
from maeri.gateware.platform.generic.serial_link import SerialLink
from maeri.gateware.platform.generic.interface_controller import InterfaceController
from maeri.gateware.platform.generic.load_afifo import LoadAfifo
from maeri.gateware.platform.generic.store_afifo import StoreAfifo
from maeri.gateware.platform.generic.status_unit import StatusUnit

from maeri.common.domains import comm_domain, comm_period
from maeri.common.domains import compute_domain, compute_period

class Top(Elaboratable):
    def __init__(self):
        max_packet_size = 32
        mem_width = 32
        mem_depth = 1024 + 512 + 256

        # config
        config = {}
        config['b_in_packet'] = max_packet_size
        config['b_in_line'] = mem_width//8
        config['m_depth'] = mem_depth
        # TODO : retrieve actual parameter from submodule
        # instantiation
        config['ports'] = 0
        config['no.mults'] = 0

        if ((mem_depth*(mem_width//8)) % max_packet_size):
            raise ValueError("MEM_SIZE MUST BE A MULTIPLE OF MAX_PACKET_SIZE")

        # instantiate submodules
        self.mem = mem = Mem(width=mem_width, depth=mem_depth, sim_init=False)
        self.serial_link = SerialLink(sim=False, max_packet_size=max_packet_size)
        self.load_unit = \
            Load(mem.addr_shape, mem.data_shape, max_packet_size)
        self.store_unit = \
            Store(mem.addr_shape, mem.data_shape, max_packet_size)
        self.interface_controller = \
            InterfaceController(mem.addr_shape, mem.data_shape, 
            max_packet_size, mem_depth, config)
        self.load_afifo = \
            LoadAfifo(mem.addr_shape, mem.data_shape, max_packet_size=max_packet_size,
            comm_domain=comm_domain, compute_domain=compute_domain)
        self.store_afifo = \
            StoreAfifo(mem.addr_shape, mem.data_shape, max_packet_size=max_packet_size,
            comm_domain=comm_domain, compute_domain=compute_domain)
        self.status_unit = \
            StatusUnit(comm_domain, compute_domain)

        # parameters
        self.max_packet_size = max_packet_size
    
    def elaborate(self, platform):
        m = Module()

        # attach submodules
        m.submodules.serial_link = serial_link = self.serial_link
        m.submodules.mem = mem = DomainRenamer(compute_domain)(self.mem)
        m.submodules.load_unit = load_unit = \
            DomainRenamer(comm_domain)(self.load_unit)
        m.submodules.store_unit = store_unit = \
            DomainRenamer(comm_domain)(self.store_unit)
        m.submodules.interface_controller = interface_controller = \
            DomainRenamer(comm_domain)(self.interface_controller)
        m.submodules.load_afifo = load_afifo = self.load_afifo
        m.submodules.store_afifo = store_afifo = self.store_afifo
        m.submodules.status_unit = status_unit = self.status_unit

        # interface_controller <> serial_link
        m.d.comb += serial_link.rx.connect(interface_controller.rx_link)
        m.d.comb += interface_controller.tx_link.connect(serial_link.tx)

        # connect up store unit
        # (interface_controller serial) <> (store_unit serial)
        m.d.comb += interface_controller.rx_ldst.connect(store_unit.rx)
        # (interface_controller upload control) <> (store_unit upload control)
        m.d.comb += store_unit.control.connect(interface_controller.download_control)
        # store unit <> afifo
        m.d.comb += mem.write_port2.connect(store_afifo.compute_domain_wp)
        #  afifo <> memory
        m.d.comb += store_afifo.comm_domain_wp.connect(store_unit.wp)

        # connect up load unit
        # (interface_controller serial) <> (load_unit serial)
        m.d.comb += load_unit.tx.connect(interface_controller.tx_ldst)
        # (interface_controller upload control) <> (load_unit upload control)
        m.d.comb += load_unit.control.connect(interface_controller.upload_control)
        # load unit <> afifo
        m.d.comb += load_unit.rp.connect(load_afifo.comm_domain_rp)
        # afifo <> memory
        m.d.comb += load_afifo.mem_domain_rp.connect(mem.read_port2)

        # interface_controller <> status_unit
        m.d.comb += status_unit.write_start_command.eq(
                        interface_controller.command_compute_start)
        m.d.comb += interface_controller.read_compute_status.eq(
                         status_unit.read_compute_status)
        
        # temporary
        m.d.comb += status_unit.write_compute_status.eq(2)
    
        return m

    def ports(self):
        rx = [self.serial_link.rx[sig] for sig in self.serial_link.rx.fields]
        tx = [self.serial_link.tx[sig] for sig in self.serial_link.tx.fields]
        return rx + tx

if __name__ == "__main__":
        from luna.gateware.platform.tinyfpga import TinyFPGABxPlatform
        top = Top()
        platform = TinyFPGABxPlatform()

        # don't map one AFIFO per BRAM
        import os
        folder = os.path.dirname(__file__)
        with open(f"{folder}/brams.txt") as f:
            platform.add_file("brams.txt", f.read())

        platform.build(top, do_program=True, 
                synth_opts=" -run begin:map_bram",
                script_after_synth=\
                    "memory_bram -rules brams.txt\n" + 
                    "techmap -map +/ice40/brams_map.v\n" +
                    "ice40_braminit\n" + 
                    "synth_ice40 -run map_ffram:\n"
                    )
