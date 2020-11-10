from enum import IntEnum, unique

bytes_in_address = None

class InitISA():
    def __init__(self, _bytes_in_address):
        global bytes_in_address
        bytes_in_address = _bytes_in_address


@unique
class Opcodes(IntEnum):
    reset = 1
    configure_states = 2
    configure_weights = 3
    load_features = 4
    store_features = 5
    run = 6

class Reset():
    op = Opcodes.reset

class ConfigureStates():
    op = Opcodes.configure_states

    def __init___(self, address):
        self.address = address

    @staticmethod
    def increment_pc():
        return bytes_in_address + 1

class ConfigureWeights():
    op = Opcodes.configure_weights

    def __init___(self, address):
        self.address = address

    @staticmethod
    def increment_pc():
        return bytes_in_address + 1

class LoadFeatures():
    op = Opcodes.load_features

    def __init___(self, port_buffer_address, num_lines, address):
        self.port_buffer_address = port_buffer_address
        self.num_lines = num_lines
        self.address = address

    @staticmethod
    def increment_pc():
        return bytes_in_address + 3

class StoreFeatures():
    op = Opcodes.store_features

    def __init___(self, port_buffer_address, num_lines, address):
        self.port_buffer_address = port_buffer_address
        self.num_lines = num_lines
        self.address = address

    @staticmethod
    def increment_pc():
        return bytes_in_address + 3

class Run():
    op = Opcodes.run

    def __init__(self, length):
        self.length = length

    @staticmethod
    def increment_pc():
        return 1