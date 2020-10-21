def prefix_record_name(record, prefix):
    """
    allow intelligent naming of luna streamer
    interfaces during simulation
    """
    if not (type(prefix) == str):
        raise TypeError("prefix name must be a string")

    for sig in record.fields:
        obj = record.fields[sig]
        setattr(obj, 'name', prefix + '_' + obj.name)

def print_sig(sig, format=None,newline=True):
    """
    allows easy intelligent printing
    of a signal during simulation
    Example:
        >>> yield from print(mysig)
        (sig mysig) = 1
    """

    if format == None:
        print(f"{sig.__repr__()} = {(yield sig)}",end='\t')
    else:
        print(f"{sig.__repr__()} = {format((yield sig))}",end='\t')
    
    if newline:
        print()

