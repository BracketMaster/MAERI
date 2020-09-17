from nmigen import Record, Signal, Module, Elaboratable
from nmigen import Array

from luna.gateware.stream import StreamInterface
from maeri.gateware.platform.generic.interfaces import PacketUpload, PacketDownload
from maeri.common.helpers import prefix_record_name

from functools import reduce
from enum import IntEnum, unique
from json import dumps
from math import ceil

from maeri.common.enums import MaeriState

@unique
class Command(IntEnum):
    Empty = 0
    Download = 1
    Upload = 2

@unique
class ParseState(IntEnum):
    GetCommand = 0
    GetLen = 1
    GetAdress = 2

class InterfaceController(Elaboratable):
    """
    The InterfaceController can do a few things.
     - examine opcodes parsed from packets to 
     determine execution direction
     - store packets to memory
     - command the MAERI core to begin execution
    """

    def __init__(self, addr_shape, data_shape, max_packet_size, depth, config):
        # some validation
        if addr_shape < 8:
            raise ValueError("MEMORY MUST HAVE AT LEAST 256 ENTRIES")

        # serial link signals
        self.rx_link = StreamInterface()
        self.tx_link = StreamInterface()
        prefix_record_name(self.rx_link, 'interface_rx_link')
        prefix_record_name(self.tx_link, 'interface_tx_link')

        # packet_ldst link signals
        self.rx_ldst = StreamInterface()
        self.tx_ldst = StreamInterface()
        prefix_record_name(self.rx_ldst, 'interface_rx_ldst')
        prefix_record_name(self.tx_ldst, 'interface_tx_ldst')

        # packet_ldst control signal
        self.upload_control = \
            PacketUpload(addr_shape, max_packet_size, 'upload_control')
        self.download_control = \
            PacketDownload(addr_shape, max_packet_size, 'download_control')

        # maeri core status signals
        self.command_compute_start = Signal()
        self.read_compute_status = Signal(MaeriState)

        # parameters
        self.config = config
        self.max_packet_size = max_packet_size
        self.addr_shape = addr_shape
        bytes_in_mem_line = data_shape/8
        self.words_in_packet, r = divmod(max_packet_size, bytes_in_mem_line)
        self.words_in_packet = int(self.words_in_packet)
        if r:
            raise ValueError("MAX PACKET SIZE IS NOT MULTIPLE OF MEM WORD SIZE")

        bytes_in_mem = int(bytes_in_mem_line)*depth
        self.packets_in_mem = bytes_in_mem//max_packet_size

    def elaborate(self, platform):
        self.m = m = Module()

        token = Array([Signal(8,name=f"subtoken_{_}") for _ in range(8)])
        letter_index = Signal(range(8))
        self.address = address = Signal(self.addr_shape)
        self.length = length = Signal(self.addr_shape)
        packet_count = Signal(range(self.packets_in_mem))

        # config data
        config = Array(dumps(self.config).encode('utf-8'))
        config_packets = len(config)
        if len(config) > 255:
            raise ValueError("Config string too long!!")
        config_index = Signal(range(len(config)))

        # bookeeping
        command = Signal(Command)
        parse_state = Signal(ParseState)

        with m.FSM(name='LEX/PARSE/CONFIG_LEN/CONFIG/DOWNLOAD/UPLOAD/START/GET_STATUS'):
            with m.State('LEX'):
                m.d.comb += self.rx_link.ready.eq(1)
                with m.If(self.rx_link.valid):
                    m.d.sync += token[letter_index].eq(self.rx_link.payload)
                    m.d.sync += letter_index.eq(letter_index + 1)
                with m.If(self.rx_link.last):
                    m.next = 'PARSE'
            
            with m.State('PARSE'):

                match_download = self.parse_command(token, Array(b'download'))
                match_upload = self.parse_command(token, Array(b'upload'))
                match_config = self.parse_command(token, Array(b'r_config'))
                match_start = self.parse_command(token, Array(b'do_start'))
                match_status = self.parse_command(token, Array(b'r_status'))

                with m.If(parse_state == ParseState.GetCommand):
                    m.d.sync += self.reset(token)
                    m.d.sync += self.reset(letter_index)

                    with m.If(match_download):
                        m.d.sync += command.eq(Command.Download)
                        m.d.sync += parse_state.eq(ParseState.GetAdress)
                        m.next = 'LEX'
                    with m.Elif(match_upload):
                        m.d.sync += command.eq(Command.Upload)
                        m.d.sync += parse_state.eq(ParseState.GetAdress)
                        m.next = 'LEX'
                    with m.Elif(match_config):
                        m.d.sync += self.reset(packet_count)
                        m.next = 'CONFIG_LEN'
                    with m.Elif(match_start):
                        m.next = 'START'
                    with m.Elif(match_status):
                        m.next = 'GET_STATUS'
                    with m.Else():
                        m.next = 'LEX'

                with m.If(parse_state == ParseState.GetAdress):
                    m.d.sync += self.parse_value(token, address)
                    m.next = 'LEX'

                    m.d.sync += parse_state.eq(ParseState.GetLen)

                with m.If(parse_state == ParseState.GetLen):
                    m.d.sync += self.parse_value(token, length)
                    m.d.sync += parse_state.eq(ParseState.GetCommand)
                    m.d.sync += command.eq(Command.Empty)
                    m.d.sync += self.reset(packet_count)

                    with m.If(command == Command.Download):
                        m.next = 'DOWNLOAD'
                    with m.If(command == Command.Upload):
                        m.next = 'UPLOAD'
            
            with m.State('CONFIG_LEN'):
                with m.If(self.tx_link.ready):
                    m.d.comb += self.tx_link.valid.eq(1)
                    m.d.comb += self.tx_link.first.eq(1)
                    m.d.comb += self.tx_link.last.eq(1)
                    m.d.comb += self.tx_link.payload.eq(config_packets)
                    m.next = 'CONFIG'
            
            with m.State('CONFIG'):
                with m.If(self.tx_link.ready):
                    m.d.comb += self.tx_link.first.eq(1)
                    m.d.comb += self.tx_link.last.eq(1)
                    m.d.comb += self.tx_link.valid.eq(1)
                    m.d.comb += self.tx_link.payload.eq(config[config_index])
                    m.d.sync += config_index.eq(config_index + 1)
                
                with m.If(config_index == len(config)):
                    m.d.sync += self.reset(config_index)
                    m.next = 'LEX'

            with m.State('DOWNLOAD'):
                m.d.comb += self.enable_link(self.rx_ldst, self.tx_ldst)
                m.d.comb += self.enable_download(base_address=address)
                with m.If(self.download_control.finished):
                    m.d.sync += packet_count.eq(packet_count + 1)
                    m.d.sync += address.eq(address + int(self.words_in_packet))
                    with m.If(packet_count == (length - 1)):
                        m.next = 'LEX'
            
            with m.State('UPLOAD'):
                m.d.comb += self.enable_link(self.rx_ldst, self.tx_ldst)
                m.d.comb +=\
                    self.enable_upload(base_address=address, num_words=self.words_in_packet)
                with m.If(self.upload_control.finished):
                    m.d.sync += packet_count.eq(packet_count + 1)
                    m.d.sync += address.eq(address + int(self.words_in_packet))
                    with m.If(packet_count == (length - 1)):
                        m.next = 'LEX'
            
            with m.State('START'):
                m.d.comb += self.command_compute_start.eq(1)
                m.next = 'LEX'
            
            with m.State('GET_STATUS'):
                with m.If(self.tx_link.ready == 1):
                    m.d.comb += self.tx_link.valid.eq(1)
                    m.d.comb += self.tx_link.payload.eq(self.read_compute_status)
                    m.d.comb += self.tx_link.first.eq(1)
                    m.d.comb += self.tx_link.last.eq(1)
                    m.next = 'LEX'

        return m
    
    def enable_link(self, rx, tx):
        statements = []
        statements += [self.rx_link.connect(rx)]
        statements += [tx.connect(self.tx_link)]
        return statements
    
    def enable_download(self, base_address):
        """
        initiates storage of a single
        packet to memory starting at 
        the base address
        """
        statements = []
        statements += [self.download_control.ptr.eq(base_address)]
        statements += [self.download_control.download.eq(1)]
        return statements
    
    def enable_upload(self, base_address, num_words):
        statements = []
        statements += [self.upload_control.ptr.eq(base_address)]
        statements += [self.upload_control.upload.eq(1)]
        statements += [self.upload_control.len.eq(num_words)]
        return statements
    
    def parse_command(self, token, pattern):
        m = self.m
        name = ''.join([chr(el) for el in pattern])
        match_by_char = Signal(len(pattern))

        zipped = zip(token[:len(token)], pattern, match_by_char)
        for sig_tok, sig_pat, sig_match in zipped:
            m.d.comb += sig_match.eq(sig_tok == sig_pat)
        
        match = Signal(1, name=f"match_{name}")
        m.d.comb += match.eq(match_by_char.all())
        
        return match
    
    def reset(self, signal):
        statements = []

        if type(signal) == Array:
            for sig in signal:
                statements += [sig.eq(sig.reset)]
        
        else:
            statements += [signal.eq(signal.reset)]
        
        return statements

    def parse_value(self, token, address):
        # split adress into groups of 8
        statements = []
        q, r = divmod(self.addr_shape, 8)

        for sig,index in zip(token, range(q)):
            statements += [address[index*8:(index + 1)*8].eq(sig)]
        
        if r:
            statements += [address[q*8 : (q*8) + r].eq(token[q][:r])]
        
        return statements