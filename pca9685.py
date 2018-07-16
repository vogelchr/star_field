#!/usr/bin/python
import math
import smbus
import time

import numpy as np

# REGS = [
#     ('MODE1', 0x00),
#     ('MODE2', 0x01),
#     ('SUBADR1', 0x02),
#     ('SUBADR2', 0x03),
#     ('SUBADR3', 0x04),
#     ('ALLCALLADR', 0x05)
# ]
#
# for i in range(16):
#     REGS.append(('LED%d_ON_L' % (i), 0x06 + 4 * i))
#     REGS.append(('LED%d_ON_H' % (i), 0x07 + 4 * i))
#     REGS.append(('LED%d_OFF_L' % (i), 0x08 + 4 * i))
#     REGS.append(('LED%d_OFF_L' % (i), 0x09 + 4 * i))
# REGS.append(('ALL_LED_ON_L', 0xfa))
# REGS.append(('ALL_LED_ON_H', 0xfb))
# REGS.append(('ALL_LED_OFF_L', 0xfc))
# REGS.append(('ALL_LED_OFF_H', 0xfd))
# REGS.append(('PRE_SCALE', 0xfe))
# REGS.append(('TestMode', 0xff))

LEDnBASE = lambda n: 0x06 + 4 * n

class PCA9685:
    def __init__(self, bus, addr=0x40):
        self.bus = bus
        self.addr = addr
        self.init_chip()
        self.onoff_regs = np.zeros((16, 4), np.uint8)

    def init_chip(self):
        # MODE1 RESTART=0, EXTCLK=0, AI=1, SLEEP=0, SUB1..3=0, ALLCALL=0
        self.bus.write_byte_data(self.addr, 0x00, 0x20)
        # MODE2
        self.bus.write_byte_data(self.addr, 0x01, 0x10)  # invert, totem pole

    def update(self, data):
        if type(data) != np.ndarray :
            data = np.array(data, dtype='i')

        # registers are ON_L, ON_H, OFF_L, OFF_H
        self.onoff_regs[:,2] = data & 0xff
        self.onoff_regs[:,3] = (data >> 8) & 0xff
        bus.write_i2c_block_data(self.addr, LEDnBASE(0), self.onoff_regs.tobytes())


def regs_normalized(v):
    v = v ** 3
    r = max(0, min(0xfff, int(v * float(0x1000) - 0.5)))
    return [0x00, 0x00, r & 0xff, r >> 8]


def main():
    bus = smbus.SMBus(0)

    t = 0.0
    N = 8
    while True:
        vals = list()
        for i in range(N):
            v = 0.5 * math.sin(t + i * 2 * math.pi / N) + 0.5
            v = v ** 5
            vals += regs_normalized(v)
        bus.write_i2c_block_data(0x40, LEDnBASE(0), vals)

        t += math.pi / 50
        if t > 2 * math.pi:
            t -= 2 * math.pi
        time.sleep(0.05)


if __name__ == '__main__':
    main()
