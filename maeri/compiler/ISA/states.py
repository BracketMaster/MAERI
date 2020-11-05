from enum import IntEnum, unique

"""
The following state table for addernodes
is implemented below with int enums.

+-------+-------+---------+
| State |   Up  | Forward |
+-------+-------+---------+
| 0     | L+R   | 0       |
+-------+-------+---------+
| 1     | 0     | L+R     |
+-------+-------+---------+
| 2     | L+R+F | 0       |
+-------+-------+---------+
| 3     | L     | R       |
+-------+-------+---------+
| 4     | R     | L       |
+-------+-------+---------+

States that result in the value ZERO on
an up or forwarding link are not captured.
"""


class ConfigUp(IntEnum):
    sum_l_r = 0
    sum_l_r_f = 2
    l = 3
    r = 4

class ConfigForward(IntEnum):
    sum_l_r = 1
    r = 3
    l = 4

@unique
class MaeriState(IntEnum):
    IDLE = 0
    BUSY = 1
    DONE = 2
