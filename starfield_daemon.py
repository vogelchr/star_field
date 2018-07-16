#!/usr/bin/python
import random
import select
import smbus
import time

import evdev

import pca9685

NUM_CHANS = 48
NUM_CHIPS = (NUM_CHANS + 15) // 16

key_actions = {
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
    83: 'random',
    #    96: 'KP_ENTER',
    78: 'bright',
    74: 'dim',
    #   55: 'KP_MULT',
    #    98: 'KP_DIV'
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


def read_constellations(fn, mapping):
    ret = list()
    with open('constellations.txt', 'rt') as f:
        curr_const = None
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('@'):
                if curr_const:
                    ret.append(curr_const)
                curr_const = [0.0 for v in range(NUM_CHANS)]
                continue
            star_num = int(line)
            star_ch = mapping[star_num]
            curr_const[star_ch] = 1.0
    if curr_const:
        ret.append(curr_const)
    return ret


# multiply accumulate
def vector_mac(acc, v, m=1.0):
    for k in range(len(acc)):
        acc[k] += v[k] * m


# vector difference (scaled by factor)
def vector_diff(a, b, fact=1.0):
    return [(va - vb) * fact for va, vb in zip(a, b)]


# normalized led brightness to PWM value (scales like third power)
def normalized_to_pwm(arr, bright=1.0):
    return [int(0.5 + (4095.0 * (min(1.0, max(0.0, v * bright)) ** 3))) for v in arr]


class LED_Fader:
    def __init__(self, bus, nchan, bright=1.0):
        self.nchans = nchan
        self.nchips = (nchan + 15) // 16
        self.chips = [pca9685.PCA9685(bus, 0x40 + k) for k in range(self.nchips)]
        self.curr = [0.0 for v in range(nchan)]

        self.brightness = bright

        self.fade_delta = None  # increment/second for fade
        self.fade_start = None  # absolute time the fade has started
        self.fade_time = None  # nominal fade time in seconds
        self.fade_done = None  # time of fade already processed (in seconds)

    def start_fade(self, tgt, now, fade_time):
        self.fade_delta = vector_diff(tgt, self.curr, 1.0 / fade_time)
        self.fade_start = now
        self.fade_done = 0.0  # how much of fade_time has already been accounted for
        self.fade_time = fade_time  # total fade time

    def set_brightness(self, bright):
        self.brightness = bright
        self.chip_update()

    def fade_update(self, now):
        delta_t = now - self.fade_start

        if delta_t >= self.fade_time:
            self.fade_start = None
            delta_t = self.fade_time

        vector_mac(self.curr, self.fade_delta, delta_t - self.fade_done)  # add some more
        self.chip_update()
        self.fade_done = delta_t

    def chip_update(self):
        led_pwm = normalized_to_pwm(self.curr, self.brightness)
        for k in range(self.nchips):
            self.chips[k].update(led_pwm[k * 16:(k + 1) * 16])

    def is_busy(self):
        return self.fade_start is not None


class Evdev_Keyboard:
    def __init__(self):
        self.keyboard = None
        self.last_active = None

        # open keyboard (if present)
        all_devs = evdev.list_devices()
        if len(all_devs) > 0:
            print('Opening keyboard at', all_devs[0])
            self.keyboard = evdev.InputDevice(all_devs[0])
            self.keyboard.grab()
        else:
            print('No keyboard connected!')

    def poll(self, sleeptime):
        if self.keyboard is None:
            time.sleep(sleeptime)
            return None

        rd, wr, ex = select.select([self.keyboard], [], [], sleeptime)
        if self.keyboard in rd:
            for ev in self.keyboard.read() :
                # drain queue
                pass

            ak = self.keyboard.active_keys()

            if not ak:
                self.last_active = None
                return None

            if ak[0] != self.last_active:
                self.last_active = ak[0]
                return ak[0]


def main():
    # read star to channel mapping table
    mapping = read_star_mapping('mapping.txt')
    print('Read %d channels from mappint file.' % len(mapping))

    constellations = read_constellations('constellations.txt', mapping)
    print('Read %d constellations.' % len(constellations))

    brightness = 0.5
    frame = LED_Fader(smbus.SMBus(0), max(mapping.values()) + 1, brightness)
    print('LED frame has %d channels, %d chips.' % (frame.nchans, frame.nchips))
    frame.chip_update()

    keyboard = Evdev_Keyboard()

    ###
    # time per frame in seconds
    ###
    last_key_pressed = None  # last pressed keyboard button

    now = time.time()
    last_key = now
    frame.start_fade(constellations[0], now, 1.0)

    while True:
        if frame.is_busy():
            frame.fade_update(now)
            sleeptime = 0.05
        else:
            sleeptime = 5.0

        key = keyboard.poll(sleeptime)
        now = time.time()

        # if no key was pressed for two minutes, load a random constellation
        if key is None :
            if now - last_key > 120 :
                last_key = now
                ix = random.randint(0, len(constellations)-1)
                frame.start_fade(constellations[ix], now, 5.0)
        else :
            last_key = now

        action = key_actions.get(key)
        if type(action) == int :
            if action >= 1 and action <= len(constellations):
                frame.start_fade(constellations[action - 1], now, 1.0)
            if action == 0 :
                tgt = [ 0.0 for v in range(frame.nchans) ]
                frame.start_fade(tgt, now, 1.0)



        if action == 'bright' :
            brightness = min(1.0, brightness + 0.1)
            frame.set_brightness(brightness)
        if action == 'dim' :
            brightness = max(0.1, brightness - 0.1)
            frame.set_brightness(brightness)
        if action == 'random' :
            tgt = [ random.uniform(0.0, 1.0) for v in range(frame.nchans) ]
            frame.start_fade(tgt, now, 1.0)


if __name__ == '__main__':
    main()
