from maeri.common.config import platform
from maeri.drivers.driver import Driver

import unittest

driver = Driver(platform)
from random import randint as r
length = 32*3
sent = [r(0, 0xFF) for _ in range(length)]

class TestMem(unittest.TestCase):
    def test_fullmem(self):
        print(f"length = {length}")
        print(f"status = {driver.get_status()}")
        driver.start_compute()
        driver.write(0, sent)
        returned = driver.read(0, length//driver.max_packet_size)
        print(f"len(sent) = {len(sent)}")
        print(f"len(returned) = {len(returned)}")
        assert(sent == returned)

if __name__ == "__main__":
    unittest.main()