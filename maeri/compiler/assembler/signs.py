def to_signed(input_value: int, num_bits: int) -> int:
    """
    For 8-bits, takes values on [0, 255]
    and returns values on [-128, 127]
    """
    min = 0
    max = 2**num_bits - 1
    assert(min <= input_value <= max)
    t = 2**(num_bits - 1) - 1
    if input_value > t:
        return (2**num_bits - input_value) * (-1)
    return input_value

def to_unsigned(input_value, num_bits):
    """
    For 8-bits, takes values on [-128, 127]
    and returns values on [0, 255].
    """
    min = -(2**(num_bits - 1))
    max = (2**(num_bits - 1)) - 1
    assert(min <= input_value <= max)
    t = 2**(num_bits)
    if input_value < 0:
        input_value = (-input_value)&(2**(num_bits) - 1)
        return t - input_value
    input_value = input_value&(2**(num_bits - 1) - 1)
    return input_value
