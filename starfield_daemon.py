#!/usr/bin/python
import select
import random
import smbus
import time

import evdev

import pca9685

NUM_CHANS = 48
NUM_CHIPS = (NUM_CHANS + 15) // 16

keycode = {
    82: 0,  # numeric keypad 0..9
    79: 1,
    80: 2,
    81: 3,
    75: 4,
    76: 5,
    77: 6,
    71: 7,
    72: 8,
    73: 9,
    83: 'KP_COMMA',
    96: 'KP_ENTER',
    78: 'KP_PLUS',
    74: 'KP_MINUS',
    55: 'KP_MULT',
    98: 'KP_DIV'
}


def read_star_mapping(fn):
    ret = dict()
    with open(fn, 'rt') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            ch, star = line.split(None, 2)
            ret[int(star)] = int(ch)
    return ret


# multiply accumulate
def vector_mac(acc, v, m=1.0):
    for k in range(len(acc)):
        acc[k] += v[k] * m


def vector_diff(a, b, fact):
    return [(va - vb) * fact for va, vb in zip(a, b)]


def normalized_to_pwm(arr):
    return [int(0.5 + (4095.0 * (min(1.0, max(0.0, v)) ** 3))) for v in arr]


def main():
    # open i2c bus, create instances for all chips
    bus = smbus.SMBus(0)
    chips = [pca9685.PCA9685(bus, 0x40 + k) for k in range(NUM_CHIPS)]

    ###
    # current LED values for a frame, the target to fade to, the increment per step
    # and the number of steps to fade
    ###
    led_frame_curr = [0.0 for v in range(NUM_CHANS)]
    led_frame_tgt = None
    led_frame_inc = None
    led_frame_ctr = 0

    # read star to channel mapping table
    mapping = read_star_mapping('mapping.txt')
    print('Read %d channels from mappint file.' % len(mapping))

    constellations = list()
    curr_const_ix = 0

    with open('constellations.txt', 'rt') as f:
        constellation_pattern = None

        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('@'):
                if constellation_pattern:
                    constellations.append(constellation_pattern)
                constellation_pattern = [0.0 for v in range(NUM_CHANS)]
                continue
            star_num = int(line)
            star_ch = mapping[star_num]
            constellation_pattern[star_ch] = 1.0
    if constellation_pattern:
        constellations.append(constellation_pattern)

    print('')

    # open keyboard (if present)
    all_devs = evdev.list_devices()
    if len(all_devs) > 0:
        print('Opening keyboard at', all_devs[0])
        keyboard = evdev.InputDevice(all_devs[0])
        keyboard.grab()
    else:
        print('No keyboard connected!')
        keyboard = None

    ###
    # time per frame in seconds
    ###
    delta_t_frame = 0.05
    t_frame = time.time()
    last_key_pressed = None  # last pressed keyboard button

    while True:
        now = time.time()
        if now >= t_frame:
            ###
            # do the frame update!
            ###
            t_frame += delta_t_frame

            if led_frame_tgt is not None:
                led_frame_ctr = 10
                led_frame_inc = vector_diff(led_frame_tgt, led_frame_curr, 1.0 / (led_frame_ctr - 1))
                led_frame_tgt = None

            if led_frame_ctr > 0:
                vector_mac(led_frame_curr, led_frame_inc)
                led_frame_ctr -= 1
                led_pwm = normalized_to_pwm(led_frame_curr)
                for k in range(NUM_CHIPS):
                    chips[k].update(led_pwm[k * 16:(k + 1) * 16])

        if now >= t_frame:  # too late!
            print('late!')
            t_frame = now
            sleeptime = 0.0
        else:
            sleeptime = t_frame - now

        ###
        # check if there is keyboard input
        ###
        if keyboard:
            rdlist = [keyboard]
        else:
            rdlist = []
        rd, wr, ex = select.select(rdlist, [], [], sleeptime)

        if keyboard in rd:
            keyboard.read()
            ak = keyboard.active_keys()
            if len(ak) == 1 and last_key_pressed is not ak[0]:
                last_key_pressed = ak[0]
                keyinfo = keycode.get(last_key_pressed)
                if type(keyinfo) == str and keyinfo == 'KP_MULT' :
                    led_frame_tgt = [ random.uniform(0.0, 1.0) for v in range(NUM_CHANS) ]
                if type(keyinfo) == int :
                    constno = keyinfo - 1
                    if constno >= 0 and constno < len(constellations) :
                        led_frame_tgt = constellations[constno]


if __name__ == '__main__':
    main()
