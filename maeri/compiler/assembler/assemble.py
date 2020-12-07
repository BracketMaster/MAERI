from maeri.compiler.assembler import opcodes
from maeri.compiler.assembler.opcodes import Opcodes, ConfigureStates
from maeri.compiler.assembler.opcodes import ConfigureWeights, LoadFeatures
from maeri.compiler.assembler.opcodes import StoreFeatures, Run, Debug
from maeri.compiler.assembler.opcodes import ConfigureCollectors
from maeri.compiler.assembler.signs import to_unsigned

valid_ops = {ConfigureStates, ConfigureWeights, LoadFeatures, 
            StoreFeatures, Run, Debug, ConfigureCollectors}

DEBUG = False

def assemble(list_of_ops, as_bytes=False):
    instr_mem = []
    instr_mem_size = 128

    config_mem = []
    config_mem_size = 128

    final_mem = []

    program_counter = 0
    config_counter = 0
    config_offset = instr_mem_size

    if opcodes.bytes_in_address != 3:
        raise RuntimeError("CURRENTLY ONLY SUPPORTING 3 BYTE ADDRESSES")
    if opcodes.num_nodes != 63:
        raise RuntimeError("CURRENTLY ONLY SUPPORTING TREES OF DEPTH 6")
    if opcodes.INPUT_WIDTH != 8:
        raise RuntimeError("CURRENTLY ONLY SUPPORTING WIDTHS OF 8")
    if opcodes.num_ports != 16:
        raise RuntimeError("CURRENTLY ONLY SUPPORTING TREES WITH 16 PORTS")

    for op in list_of_ops:
        assert(type(op) in valid_ops)

        if type(op) in {ConfigureStates}:
            instr_mem += [opcodes.ConfigureStates.op]
            address = list(int(config_offset).to_bytes(3, 'little'))
            instr_mem += address

            config_mem += [int(conf) for conf in op.states] + [0]
            config_offset += 64//4

        if type(op) in {ConfigureWeights}:
            instr_mem += [opcodes.ConfigureWeights.op]
            address = list(int(config_offset).to_bytes(3, 'little'))
            instr_mem += address

            weights = [0,0,0] + [int(conf) for conf in op.weights] + [0]
            weights = [to_unsigned(weight, opcodes.INPUT_WIDTH) for weight in weights]
            config_mem += weights
            config_offset += 36//4

        if type(op) in {ConfigureCollectors}:
            instr_mem += [opcodes.ConfigureCollectors.op]
            address = list(int(config_offset).to_bytes(3, 'little'))
            instr_mem += address

            config_mem += [int(conf) for conf in op.states] + [0]
            config_offset += 16//4
        
        if type(op) in {Debug}:
            instr_mem += [opcodes.Debug.op]
    
    instr_mem += [opcodes.Reset.op]
    instr_mem += (4*instr_mem_size - len(instr_mem))*[0]

    config_mem += (4*config_mem_size - len(config_mem))*[0]

    combined_mem = instr_mem + config_mem
    if as_bytes:
        return combined_mem

    for mem_line in range(instr_mem_size + config_mem_size):
        array = combined_mem[mem_line*4 : (mem_line + 1)*4]
        final_mem += [int.from_bytes(bytearray(array), 'little')]

    if DEBUG:
        for line in range(len(final_mem)//4):
            offset = line*4

            data = ""
            for addr in range(4):
                data += f" {offset + addr} : {hex(final_mem[offset + addr])}\t"
            print(data)

    return final_mem