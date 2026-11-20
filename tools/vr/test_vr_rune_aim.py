#!/usr/bin/env python3
"""The runes' aim, in the game against fake_xr (runtime/nvn/vulkan/exec.c rune_pick_aim, runtime/vr/vr_camera.c).

While a rune is aimed (L held), the game reads its G-buffer at one point of the picture to pick Stasis', Magnesis'
and Cryonis' target. In VR that point is the eye's own axis, and while a rune is aimed each eye's field is made
symmetric, so it is the picture's centre - where the game draws its reticle - whatever the hand does: fake_xr's right
hand, the head held still, points ahead, 35 degrees up and 35 degrees down in turn. Passes when the pick was set by
VR, sat at the centre (0.5 0.5) once the aim had begun, did not follow the hand, and no ray was drawn (no dots).
(Aimed by the hand, Magnesis took nothing: its target is also taken along the view and Link's hand; 2026-11-20.)

  python tools/vr/test_vr_rune_aim.py --save <scratch save> [--out build/vr/rune_aim] [--stereo]
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import perf_routes  # noqa: E402

PITCH = {'ahead': 0, 'up': 35, 'down': -35}


def script():
    lines = ['0 head 0 1.7 0 0 0 0', '0 hand left -0.25 1.2 -0.3 0 0 0']
    for k in range(300):   # ahead, up, down: 4 s each, over and over (the game's boot takes a while)
        for i, ph in enumerate(('ahead', 'up', 'down')):
            t = 12.0 * k + 4 * i
            for dt in (0.01, 3.99):
                lines.append('%.2f hand right 0.25 1.3 -0.3 0 %d 0' % (t + dt, PITCH[ph]))
    return sorted(lines, key=lambda line: float(line.split()[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/rune_aim')
    ap.add_argument('--stereo', action='store_true')
    a = ap.parse_args()
    env = {'SAVAGEWIND_VR_LOG_RUNE_AIM': '1', 'SAVAGEWIND_VR_MOTION': '0'}
    if a.stereo:
        env['SAVAGEWIND_VR_STEREO'] = '1'
    out = a.out
    game, proc, log = re_run.boot(a.save, out, env, script())
    try:
        game.cmd('hold', 'l', ok=False)
        time.sleep(3.0)
        mark = os.path.getsize(os.path.join(out, 'game.log'))
        time.sleep(14.0)
        v = game.cmd('vr', ok=False, timeout=60)
        aims, dots = int(v.get('rune_aims', 0)), int(v.get('arc_frames', 0))
        game.cmd('shot', os.path.relpath(os.path.join(os.path.abspath(out), 'aim.png'), re_run.T.TREE), ok=False)
    finally:
        game.cmd('release', 'l', ok=False)
        perf_routes.stop_game(game, proc, log)
    text = open(os.path.join(out, 'game.log'), 'rb').read().decode('utf-8', 'replace')
    first = re.findall(r'\[vr-rune\] pick at ([\d.]+) ([\d.]+)', text)
    later = re.findall(r'\[vr-rune\] pick at ([\d.]+) ([\d.]+)', text[mark:])
    print('picks logged:', ' | '.join('%s %s' % p for p in first[:8]))
    ok = True

    def check(cond, what):
        nonlocal ok
        print('  %s   %s' % ('ok' if cond else 'FAIL', what))
        ok = ok and cond

    check(aims > 0, 'the pick was set by VR (%d draws)' % aims)
    check(bool(first) and all(abs(float(u) - 0.5) < 0.005 and abs(float(w) - 0.5) < 0.005 for u, w in first[-2:]),
          "the pick at the picture's centre once aimed (%s)" % (' '.join('%s,%s' % p for p in first[-2:])))
    check(not later, 'it did not follow the hand up, ahead and down (%d changes)' % len(later))
    check(dots == 0, 'no ray drawn (%d pictures with dots)' % dots)
    print('all passed' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
