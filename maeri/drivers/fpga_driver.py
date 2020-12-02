import usb.core
import usb.util
from json import loads
from maeri.compiler.assembler import opcodes

class FPGADriver():
    def __init__(self):
        # find our device
        dev = usb.core.find(idVendor=0x16d0, idProduct=0x0f3b)

        # was it found?
        if dev is None:
            raise ValueError('FPGA device not found')

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        dev.set_configuration()

        # get an endpoint instance
        cfg = dev.get_active_configuration()
        intf = cfg[(1,0)]

        self.out = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

        self.inn = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN)
        

        config = loads(self.get_config())
        print(f"device config = {config}")
        self.max_packet_size = config['b_in_packet']
        self.mem_width = config['b_in_line']
        self.mem_depth = config['m_depth']
        self.ports = config['ports']
        self.no_mults = config['no.mults']
        self.packets_in_mem = (self.mem_depth * self.mem_width)//self.max_packet_size
        self.mem_size = self.mem_depth * self.mem_width
        opcodes.InitISA(_bytes_in_address=3,
                        _num_nodes= (2*self.no_mults) - 1,
                        _num_adders= (self.no_mults - 1),
                        _num_mults=self.no_mults,
                        _input_width=8
                        )

    def get_config(self):
        
        self.out.write(b'r_config')
        ret = list(self.inn.read(1))
        length = ret[0]

        data = []
        for count in range(length):
            data += list(self.inn.read(1))

        data = ''.join([chr(letter) for letter in data])

        return data

    def get_status(self):
        
        self.out.write(b'r_status')
        data = list(self.inn.read(8))

        return data[0]

    def start_compute(self):
        
        self.out.write(b'do_start')

        return
    
    def write(self, start_adress, data):
        if (len(data) % self.max_packet_size):
            raise ValueError("DATA MUST BE MULTIPLE OF max_packet_size")

        length = len(data) // self.max_packet_size

        self.out.write(b'download')
        self.out.write(int(start_adress).to_bytes(8, 'little'))
        self.out.write(int(length).to_bytes(8, 'little'))

        index = self.max_packet_size
        for count in range(length):
            self.out.write(data[count*index : (count + 1)*index])
    
    def read(self, start_adress, length):
        
        self.out.write(b'upload')
        self.out.write(int(start_adress).to_bytes(8, 'little'))
        self.out.write(int(length).to_bytes(8, 'little'))

        data = []
        for packet in range(length):
            data += list(self.inn.read(self.max_packet_size))

        return data