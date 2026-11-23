#!/usr/bin/env python3
"""Throwing a lifted object by hand, in the game against fake_xr.

The left grip at the left hip takes the rune out (L); with the Remote Bomb rune Link lifts a bomb over his head
(the grab action: the player's carrying flag). In first person the bomb is then drawn in the right hand
(carried_frames). The right trigger pressed and let go during a fast swing of the right hand to the right throws it
(R): the game's throw gets the hand's velocity in place of its own (hand_throws, the log's "[vr] throw: the hand's").

  python tools/vr/test_vr_throw.py --save <scratch save> [--out build/vr/throw]
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import perf_routes  # noqa: E402

SQUEEZE_L = '/user/hand/left/input/squeeze/value'
TRIGGER_R = '/user/hand/right/input/trigger/value'


def script():
    lines = ['0 head 0 1.7 0 0 0 0',
             '0 hand left -0.25 1.2 -0.3 0 0 0',
             '0 hand right 0.25 1.3 -0.3 0 0 0']
    for k in range(1, 40):
        t = 40.0 * k
        lines += [
            '%.2f hand left -0.15 1.2 0.12 0 0 0' % (t + 3.0),   # the left hip
            '%.2f value %s 1' % (t + 3.5, SQUEEZE_L),
            '%.2f value %s 0' % (t + 3.75, SQUEEZE_L),           # select the Remote Bomb (L)
            '%.2f hand left -0.15 1.2 0.12 0 0 0' % (t + 3.9),
            '%.2f value %s 1' % (t + 5.5, TRIGGER_R),            # A: bring out a bomb
            '%.2f value %s 0' % (t + 5.8, TRIGGER_R),
            '%.2f value %s 1' % (t + 7.0, TRIGGER_R),            # A again: lift it into the carrying action
            '%.2f value %s 0' % (t + 7.15, TRIGGER_R),
            '%.2f value %s 1' % (t + 8.0, TRIGGER_R),            # arm the throw while carrying
            '%.2f hand right 0.25 1.3 -0.3 0 0 0' % (t + 8.0),
            '%.2f hand right 0.95 1.35 -0.4 0 0 0' % (t + 8.35), # keep moving at release (fake_xr samples 5 ms)
            '%.2f value %s 0' % (t + 8.34, TRIGGER_R),           # let go while the hand is still swinging
            '%.2f hand left -0.9 1.2 -0.3 0 0 0' % (t + 8.6),
            '%.2f hand right 0.25 1.3 -0.3 0 0 0' % (t + 9.0),
        ]
    return sorted(lines, key=lambda line: float(line.split()[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/throw')
    a = ap.parse_args()
    env = {'SAVAGEWIND_VR_TRACE_GESTURES': '1', 'SAVAGEWIND_VR_MOTION': '1',
           'SAVAGEWIND_VR_HAND_THROW': '1', 'SAVAGEWIND_VR_CARRY_IN_HANDS': '1'}
    game, proc, log = re_run.boot(a.save, a.out, env, script())
    carrying = carried = throws = 0
    try:
        now = lambda: game.cmd('vr', ok=False).get('frames', 0) / 90.0  # noqa: E731
        base = (int(now() // 40) + 1) * 40
        while now() < base + 7.5:
            time.sleep(0.1)
        st = game.cmd('vr', ok=False)
        shot = os.path.relpath(os.path.join(os.path.abspath(a.out), 'carry.png'), re_run.T.TREE).replace(os.sep, '/')
        game.cmd('shot', shot, ok=False)
        carrying, carried = int(st.get('carrying', 0)), int(st.get('carried_frames', 0))
        while now() < base + 10.0:
            time.sleep(0.1)
        throws = int(game.cmd('vr', ok=False).get('hand_throws', 0))
    finally:
        perf_routes.stop_game(game, proc, log)

    text = open(os.path.join(a.out, 'game.log'), encoding='utf-8', errors='replace').read()
    hand = re.findall(r'\[vr\] throw: the hand\'s \(([-\d. ]+)\) in place of the game\'s \(([-\d. ]+)\)', text)
    carried_item = '[vr] carried: Item_RemoteBomb in the right hand' in text
    print('carrying at the sample:', carrying, '| frames drawn in the hand:', carried,
          '| Remote Bomb seen in the hand:', carried_item)
    print('throws given the hand\'s velocity:', throws, hand[:2])
    for line in text.splitlines():
        if '[vr] carried:' in line or '[vr] throw' in line:
            print('  ', line.strip())
    ok = carried > 0 and carried_item and throws >= 1 and hand
    if hand:   # the hand swung to the right: the throw goes that way more than the game's (Link's forward)
        hv = [float(x) for x in hand[0][0].split()]
        print('hand velocity', hv)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
