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
            '%.2f value %s 0' % (t + 3.75, SQUEEZE_L),           # the rune out (L): a bomb lifted
            '%.2f hand left -0.15 1.2 0.12 0 0 0' % (t + 3.9),
            '%.2f hand left -0.25 1.2 -0.3 0 0 0' % (t + 4.4),
            '%.2f value %s 1' % (t + 7.0, TRIGGER_R),            # the throw armed
            '%.2f hand right 0.25 1.3 -0.3 0 0 0' % (t + 7.3),   # a swing: 0.7 m to the right in 0.12 s
            '%.2f hand right 0.95 1.35 -0.4 0 0 0' % (t + 7.42),
            '%.2f value %s 0' % (t + 7.43, TRIGGER_R),           # let go: thrown
            '%.2f hand right 0.25 1.3 -0.3 0 0 0' % (t + 8.0),
        ]
    return sorted(lines, key=lambda line: float(line.split()[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/throw')
    a = ap.parse_args()
    env = {'SAVAGEWIND_VR_TRACE_GESTURES': '1', 'SAVAGEWIND_VR_MOTION': '0'}
    game, proc, log = re_run.boot(a.save, a.out, env, script())
    carrying = carried = throws = 0
    try:
        now = lambda: game.cmd('vr', ok=False).get('frames', 0) / 90.0  # noqa: E731
        base = (int(now() // 40) + 1) * 40
        while now() < base + 6.0:
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
    print('carrying after the rune came out:', carrying, '| frames drawn in the hand:', carried)
    print('throws given the hand\'s velocity:', throws, hand[:2])
    for line in text.splitlines():
        if '[vr] carried:' in line or '[vr] throw' in line:
            print('  ', line.strip())
    ok = carrying == 1 and carried > 0 and throws >= 1 and hand
    if hand:   # the hand swung to the right: the throw goes that way more than the game's (Link's forward)
        hv = [float(x) for x in hand[0][0].split()]
        print('hand velocity', hv)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
