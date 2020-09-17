from nmigen              import Elaboratable, Module

from luna                import top_level_cli
from luna.full_devices   import USBSerialDevice
from luna.gateware.stream import StreamInterface

from maeri.common.helpers import prefix_record_name

class SerialLink(Elaboratable):
    def __init__(self, sim, max_packet_size):
        self.rx = StreamInterface()
        self.tx = StreamInterface()
        prefix_record_name(self.rx, 'serial_link')
        prefix_record_name(self.tx, 'serial_link')

        # parameters
        self.sim = sim
        self.max_packet_size = max_packet_size

    def elaborate(self, platform):
        m = Module()

        if not self.sim:
            # Generate our domain clocks/resets.
            m.submodules.car = platform.clock_domain_generator()

            # Create our USB-to-serial converter.
            ulpi = platform.request(platform.default_usb_connection)
            m.submodules.usb_serial = usb_serial = \
                    USBSerialDevice(bus=ulpi, idVendor=0x16d0,
                            idProduct=0x0f3b, max_packet_size=self.max_packet_size)
            
            # connect peripherals
            m.d.comb += usb_serial.rx.connect(self.rx)
            m.d.comb += self.tx.connect.eq(usb_serial.tx)

            # ... and always connect by default.
            m.d.comb += usb_serial.connect.eq(1)

        return m
