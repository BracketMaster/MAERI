"""
Some useful casting utilities for the MAERI
compiler.
"""

def cast_float_to_fixed(bits, numpy=False):
    """
    Returns a function that converts a float
    on [-1, 1] to a binary fixed point of 
    length bits.
    """
    factor = 2**(bits - 1)

    if numpy:
        return lambda  : (factor*x).astype(int)
    return lambda x : int(factor*x)

def cast_fixed_to_float(bits):
    """
    Returns a function that converts a fixed point
    of length `bits` to a float on range [-1, 1].
    """
    factor = 2**(bits - 1)
    return lambda x : x/factor