"""
Some useful hardware models to help
with simulation.
"""

from nmigen.sim import Settle, Tick
from maeri.common.domains import comm_domain, comm_period
from maeri.common.domains import compute_domain, compute_period

def inject_packet(byte_list, rx, max_packet_size=32):
    """
    byte_list: a list of bytes or technically Python
    ints
    """
    # validate packet
    try:
        assert(len(byte_list) <= max_packet_size)
    except:
        raise ValueError(f"Packet length of {len(byte_list)} " + 
                         f"is longer than max_packet_size of {max_packet_size}")

    yield rx.valid.eq(1)
    yield Settle()

    for index, byte in enumerate(byte_list):
        while(not (yield rx.ready)):
            yield Tick(comm_domain)
            yield Settle()

        if (index == 0):
            yield rx.first.eq(1)
        else :
            yield rx.first.eq(0)
        
        yield rx.payload.eq(byte)
        yield Settle()

        if (index == (len(byte_list) - 1)):
            yield rx.last.eq(1)
        
        yield Tick(comm_domain)

    yield rx.valid.eq(0)
    yield rx.last.eq(0)

def recieve_packet(tx):
    packet_started = False
    recvd = []
    yield tx.ready.eq(1)

    while True:
        if (yield tx.valid):
            if (yield tx.first):
                packet_started = True

            if packet_started:
                recvd += [(yield tx.payload)]

            if (yield tx.last):
                break

        yield Tick(comm_domain)
    
    yield tx.ready.eq(0)
    yield Tick(comm_domain)
    return recvd