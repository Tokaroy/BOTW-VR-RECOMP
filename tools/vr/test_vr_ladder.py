#!/usr/bin/env python3
"""Ladders (C34, docs/vr/FEATURES.md), against fake_xr: on a ladder the walk stick is turned from the view's way to the
way Link faces, so forward climbs whatever the player looks at. A ladder can't be reached in the test save, so the
turn is checked on flat ground with SAVAGEWIND_VR_LADDER_TEST=1 (the turn everywhere, his body left as the game has
it): the head turned 90 deg, the stick forward must walk Link along the way he faces (`vr` link_facing), not toward the view; without the
switch the same push walks him toward the view (walk where you look). Read from `camera` (the view's yaw) and `pos`.

  python tools/vr/test_vr_ladder.py --save <scratch save> [--out build/vr/ladder]
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handsim  # noqa: E402
import test_vr_game as T  # noqa: E402


def walk(save, out, ladder):
    env = {'SAVAGEWIND_VR_STEREO': '0'}
    if ladder:
        env['SAVAGEWIND_VR_LADDER_TEST'] = '1'
    sim = handsim.Sim(save, out, env)
    try:
        sim.run('head 0 1.7 0 0 0 0')
        time.sleep(3)
        cam0 = T.camera(sim.game)
        sim.run('head 0 1.7 0 90 0 0')
        time.sleep(2)
        cam1 = T.camera(sim.game)
        p0 = sim.game.cmd('pos', ok=False)
        face = T.vr_state(sim.game).get('link_facing')
        sim.run('stick left 0 1')
        time.sleep(1.5)
        sim.run('stick left 0 0')
        time.sleep(0.5)
        p1 = sim.game.cmd('pos', ok=False)
        frames = T.vr_state(sim.game).get('ladder_frames', 0)
    finally:
        sim.stop()
    d = (p1['x'] - p0['x'], p1['z'] - p0['z'])
    n = math.hypot(*d)

    def along(cam):
        y = math.radians(cam['yaw'])
        return (d[0] * math.sin(y) + d[1] * math.cos(y)) / max(n, 1e-6)
    if face is None:
        return n, None, along(cam1), frames
    return n, along({'yaw': face}), along(cam1), frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/ladder')
    a = ap.parse_args()
    ok = True

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    n, f0, f1, fr = walk(a.save, os.path.join(a.out, 'ladder'), True)
    print('    ladder turn: walked %.2f m, along the way Link faced %s, along the turned view %.2f (%d frames turned)' %
          (n, '%.2f' % f0 if f0 is not None else '?', f1, fr))
    check(n > 0.5 and fr > 0, 'the stick walked Link with the ladder turn on (%.2f m)' % n)
    check(f0 is not None and f0 > 0.9 and f1 < 0.7,
          'forward goes the way Link faces, not where the head looks (cos %.2f along him / %.2f along the view)' %
          (f0 if f0 is not None else -9, f1))
    n, f0, f1, fr = walk(a.save, os.path.join(a.out, 'plain'), False)
    print('    plain: walked %.2f m, along the turned view %.2f (%d frames turned)' % (n, f1, fr))
    check(n > 0.5 and f1 > 0.8 and fr == 0, 'off a ladder forward still walks where you look (cos %.2f)' % f1)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
