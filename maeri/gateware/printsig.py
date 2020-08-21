"""
allows easy intelligent printing
of a signal during simulation
Example:
    >>> yield from print(mysig)
    (sig mysig) = 1
"""

def print_sig(sig, format=None,newline=True):

    if format == None:
        print(f"{sig.__repr__()} = {(yield sig)}",end='\t')
    else:
        print(f"{sig.__repr__()} = {format((yield sig))}",end='\t')
    
    if newline:
        print()