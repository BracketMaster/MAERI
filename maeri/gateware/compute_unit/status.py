from enum import IntEnum, unique

@unique
class Status(IntEnum):
    idle = 0
    configuring = 1
    loading = 2
    running = 3
    storing = 4
    done = 5