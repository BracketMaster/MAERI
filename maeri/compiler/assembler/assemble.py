from maeri.compiler.assembler import opcodes
from maeri.compiler.assembler.opcodes import Opcodes, ConfigureStates
from maeri.compiler.assembler.opcodes import ConfigureWeights, LoadFeatures
from maeri.compiler.assembler.opcodes import StoreFeatures, Run
from maeri.compiler.assembler.signs import to_unsigned

valid_ops = {Opcodes, ConfigureStates, ConfigureWeights, LoadFeatures, StoreFeatures, Run}

def assemble(list_of_ops):
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

    for op in list_of_ops:
        assert(type(op) in valid_ops)

        if type(op) in {ConfigureStates}:
            instr_mem += [int(Opcodes.configure_states)]
            address = list(int(config_offset).to_bytes(3, 'little'))
            instr_mem += address

            config_mem += [int(conf) for conf in op.states] + [0]
            config_offset += 64

        if type(op) in {ConfigureWeights}:
            instr_mem += [int(Opcodes.configure_weights)]
            address = list(int(config_offset).to_bytes(3, 'little'))
            instr_mem += address

            weights = [0,0,0] + [int(conf) for conf in op.weights] + [0]
            weights = [to_unsigned(weight, opcodes.INPUT_WIDTH) for weight in weights]
            config_mem += weights
            config_offset += 36
    
    instr_mem += [int(Opcodes.reset)]
    instr_mem += (4*instr_mem_size - len(instr_mem))*[0]

    config_mem += (4*config_mem_size - len(config_mem))*[0]

    combined_mem = instr_mem + config_mem

    for mem_line in range(instr_mem_size + config_mem_size):
        array = combined_mem[mem_line*4 : (mem_line + 1)*4]
        final_mem += [int.from_bytes(bytearray(array), 'little')]

    #print([hex(el) for el in final_mem])
    return final_mem

from maeri.common.skeleton import Skeleton
skeleton = Skeleton(
    depth=6,
    num_ports=16,
    bytes_in_line=4,
    VERBOSE=True
    )

num_nodes=len(skeleton.all_nodes)
num_adders=len(skeleton.adder_nodes)
num_mults=len(skeleton.mult_nodes)

from maeri.compiler.assembler.opcodes import InitISA
InitISA(
    _bytes_in_address=3,
    _num_nodes=num_nodes,
    _num_adders=num_adders,
    _num_mults=num_mults,
    _input_width=8
    )

# build test op list
from maeri.compiler.assembler.states import ConfigForward, ConfigUp
from maeri.compiler.assembler.states import InjectEn
from random import choice, randint

valid_adder_states = [ConfigForward.sum_l_r, ConfigForward.r, ConfigForward.l]
valid_adder_states += [ConfigUp.sum_l_r, ConfigUp.r, ConfigUp.l, ConfigUp.sum_l_r_f]
valid_mult_states = [InjectEn.on, InjectEn.off]

ops = []

test_state_vec_1 = [choice(valid_adder_states) for node in range(num_adders)]
test_state_vec_1 += [choice(valid_mult_states) for node in range(num_mults)]
ops += [ConfigureStates(test_state_vec_1)]

test_weight_vec_1 = [randint(-128, 127) for node in range(num_mults)]
ops += [ConfigureWeights(test_weight_vec_1)]

assemble(ops)