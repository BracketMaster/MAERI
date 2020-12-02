from maeri.common.config import platform
from maeri.drivers.driver import Driver

from maeri.compiler.assembler.states import ConfigForward, ConfigUp
from maeri.compiler.assembler import opcodes
from maeri.compiler.assembler.opcodes import LoadFeatures
from maeri.compiler.assembler.states import InjectEn
from maeri.compiler.assembler.assemble import assemble
from maeri.gateware.compute_unit.top import State
from random import randint, choice

# connect to device
driver = Driver(platform)

# build out ops
valid_adder_states = [ConfigForward.sum_l_r, ConfigForward.r, ConfigForward.l]
valid_adder_states += [ConfigUp.sum_l_r, ConfigUp.r, ConfigUp.l, ConfigUp.sum_l_r_f]
valid_mult_states = [InjectEn.on, InjectEn.off]

ops = []

test_state_vec_1 = [choice(valid_adder_states) for node in range(driver.no_mults - 1)]
test_state_vec_1 += [choice(valid_mult_states) for node in range(driver.no_mults)]
ops += [opcodes.ConfigureStates(test_state_vec_1)]

test_weight_vec_1 = [randint(-128, 127) for node in range(driver.no_mults)]
ops += [opcodes.ConfigureWeights(test_weight_vec_1)]
ops += [opcodes.Debug()]

# assemble ops
binary = assemble(ops, as_bytes=True)

driver.write(0, binary)
driver.start_compute()
while(driver.get_status() != State.reset):
    pass
print(driver.get_status())
states = driver.read(0,1)[:8]
#print(f"injected states = {test_state_vec_1[:4]}")
#print(f"returned states = {states}")
assert states[:4] == states[4:8]
assert states[:4] == test_state_vec_1[:4]
print("FINISHED")