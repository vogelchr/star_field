#!/usr/bin/python
import numpy as np
import os

mapping = dict()
mapping_file = 'mapping.txt'

print('***************************************')
print('* Interactive starfield test program. *')
print('***************************************')
print('')

if os.path.exists(mapping_file) :
    try :
        with open(mapping_file) as f :
            for line in f :
                if not line or line.startswith('#') :
                    continue
                arr = line.split(None, 1)
                mapping[int(arr[0])] = arr[1].strip()

        print('-- mapping loaded from file %s --'%mapping_file)
        for ch_num in sorted(mapping) :
            print(' Ch %02d -> \'%s\''%(ch_num, mapping[ch_num]))

    except Exception as e :
        print('Exception occured during load of', mapping_file)
        print('Exception:', e)
        mapping = dict()

    print('')
###
# physical output channels
###
num_ch = 16*3
chan_data = np.zeros(num_ch, dtype=float)
curr_ch = 0
next_ch = None
brightness = 255


print('Commands:')
print('   <enter> goto next channel')
print('   gNNN    goto channel NNN, valid 0..%d'%(num_ch - 1))
print('   q       exit')
print('   +/-     increase/decrease brightness of pixel')
print('   =xxxx   set mapping of this channel to star xxxx')
print('   #       remove mapping from current channel')
print('   q       quit without saving')
print('   wFILE   quit, saving to file (default: %s)'%(mapping_file))
print('   p       print mapping table')
print('   a       all on')

print('')

channel_viz_steps = ' .-*#'

while True :

    if next_ch is not None and (next_ch > num_ch or next_ch < 0) :
        print('Channel', next_ch, 'out of range!')
        next_ch = None

    if next_ch is not None :
        print('Switching to channel %d.'%(next_ch))
        curr_ch = next_ch
        chan_data[...] = 0
        chan_data[curr_ch] = 1.0
        next_ch = None

    channel_viz_ix = (np.clip(chan_data, 0.0, 1.0)*(len(channel_viz_steps)-1)+0.5).astype('i')
    channel_viz = ''.join([ channel_viz_steps[i] for i in channel_viz_ix])
    channel_num_ones  = ''.join( '%d'%(i%10) for i in range(num_ch))
    channel_num_tens  = ''.join( '%d'%(i // 10) for i in range(num_ch))

    print('Output: [%s]'%channel_viz)

    if curr_ch in mapping :
        prompt='Star \"%s\", Ch %d>'%(mapping[curr_ch], curr_ch)
    else :
        prompt='Ch %d>'%(curr_ch)
    ans = input(prompt).strip()

    if ans.startswith('p') :
        for ch_num in sorted(mapping) :
            print(' Ch %02d -> \'%s\''%(ch_num, mapping[ch_num]))
        continue

    #################################################################
    #
    # selecting individual channels an editing the mapping
    #   Commands: =, '#', gNNN, "empty"
    #
    #################################################################

    ###
    # name a star
    ###
    if ans.startswith('=') :
        star_name = ans[1:].strip()
        mapping[curr_ch] = star_name

    ###
    # remove mapping
    ###
    if ans.startswith('#') :
        if curr_ch in mapping :
            del mapping[curr_ch]

    ###
    # goto next channel, also if a star was named using '='!
    ###
    if not ans or ans.startswith('=') or ans.startswith('#') or ans.startswith('>'):
        next_ch = curr_ch + 1
    if ans.startswith('<') :
        next_ch = curr_ch - 1

    ###
    # gNNN -> goto channel
    ###
    if ans.lower().startswith('g') :
        try :
            next_ch = int(ans[1:])
        except Exception as e :
            print('Parse error:', e)
            next_ch = None

    if next_ch is not None :
        if next_ch >= num_ch :
            next_ch = 0
        if next_ch == -1 :
            next_ch = num_ch - 1
        continue

    #################################################################
    #
    # bNNN -> set brightness
    # +    -> increase brightness
    # -    -> decrease brightness
    #
    #################################################################

    if ans == '+' or ans == '-' or ans.startswith('b') :
        if ans == '+' :
            brightness = min(255, brightness + 16)
        elif ans == '-' :
            brightness = max(0, brightness - 16)
        else :
            try :
                brightness = min(255, max(0, int(ans[1:])))
            except Exception as e :
                print('Cannot parse brightness value, exception:', e)
                brightness = 255

        continue

    #################################################################
    #
    # All
    #
    #################################################################

    if ans.lower().startswith('a') :
        # set all channels
        chan_data[...] = 1.0

    #################################################################
    #
    # Quit/Exit
    #
    #################################################################

    if ans.lower().startswith('q') :
        mapping = None
        break

    if ans.lower().startswith('w') :
        if len(ans) > 1 :
            mapping_file = ans[1:]
        break

if mapping is not None :
    print('Saving mapping to \'%s\'.'%mapping_file)
    with open(mapping_file, 'wt') as f :
        print('# Ch -> Star', file=f)
        for k in sorted(mapping) :
            print(k,mapping[k], file=f)
