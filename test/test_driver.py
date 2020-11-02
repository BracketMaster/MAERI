"""
Writes 32 MB of random data to the device,
and then reads 32 MB of data back to verify
that it was correctly written
"""

from maeri.common.config import platform
from maeri.drivers.driver import Driver

import unittest

def list_ints_to_list_bytes(list_ints):
    list_bytes = []
    for val in list_ints:
        list_bytes += list(val.to_bytes(4, byteorder='little'))
    
    return list_bytes

driver = Driver(platform)
from random import randint as r

def quick_compare(l1, l2):
    diffs_by_index = []
    assert(len(l1) == len(l2))

    for index in range(len(l1)):
        if l1[index] != l2[index]:
            diffs_by_index += [index]
    
    return diffs_by_index

lines_in_KiB = 1024//driver.mem_width
KiBs = (driver.mem_width * driver.mem_depth)//1024
data = [r(0, 0xFF) for _ in range(KiBs * 1024)]

def write_data():
    for KiB in range(KiBs):
        offset_address = KiB*lines_in_KiB
        driver.write(offset_address, data[1024*KiB : 1024*(KiB + 1)])

def check_data():
    for KiB in range(KiBs):
        expected = data[1024*KiB : 1024*(KiB + 1)]
        offset_address = KiB*lines_in_KiB
        length = len(expected)
        returned = driver.read(offset_address, length//driver.max_packet_size)
        assert(returned == expected)


class TestMem(unittest.TestCase):
    def test_fullmem(self):
        print(f"Testing {KiBs} KiBs of memory.")
        print(f"status = {driver.get_status()}")

        write_data()
        check_data()

        print()
        print("TEST SUCCESS")
        print(f"VERIFIED {KiBs} KiBs OF MEMORY.")

if __name__ == "__main__":
    DEBUG = True
    unittest.main()