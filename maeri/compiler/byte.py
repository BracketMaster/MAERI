"""
Contains a class implementation of a array
manipulated byte.
"""
class Byte():
    """
    This class implements array level byte
    manipulations.

    >>> from byte import Byte as b
    >>> my_byte = b()
    >>> my_byte[5] = 1
    >>> my_byte[7:8] = [1]
    >>> print(my_byte)
    0b10100000
    >>> print(int(my_byte))
    160
    
    """
    def __init__(self):
        self.__rep = [0]*8
    
    def __getitem__(self, key):
        if type(key) is slice:
            self.__check_range(key.start, (0,7))
            self.__check_range(key.stop, (0,7))

        else:
            self.__check_range(key, (0, 7))

        return self.__rep[key]

    def __setitem__(self, key, val):
        if type(key) is slice:
            if key.stop <= key.start:
                raise IndexError("Slice stop index " + 
                                 "{} must be greater than start index {}"
                                .format(key.stop, key.start))

            self.__check_range(key.start, (0,8))
            self.__check_range(key.stop, (0,8))
        
            if type(val) is not list:
                raise TypeError(f"for slices, `val` must be type {type(list)}\n"+
                                f"not {type(val)}")
            
            if len(val) != (key.stop - key.start):
                raise ValueError("Slice length {} and list length {} mismatch."
                                .format(len(val), key.stop - key.start))

            
            for el in val:
                if el not in [0, 1]:
                    raise ValueError(f"val must be 1 or 0, not `{el}`")

        else:
            self.__check_range(key, (0, 7))
            if val not in [0, 1]:
                raise KeyError(f"val must be 1 or 0, not `{val}`")


        self.__rep[key] = val
    
    def __int__(self):
        r = [str(bit) for bit in self.__rep]
        r.reverse()
        r = '0b' + ''.join(r)
        return int(r, base=0)
    
    def __str__(self):
        r = [str(bit) for bit in self.__rep]
        r.reverse()
        return '0b' + ''.join(r)

    def __repr__(self):
        r = [str(bit) for bit in self.__rep]
        r.reverse()
        return '0b' + ''.join(r)
    
    def __check_range(self, key, _range):
        if (key > _range[1]) or (key < _range[0]):
            raise Exception(f"Index `{key}` is not on domain [{_range[0]},{_range[1]}]")