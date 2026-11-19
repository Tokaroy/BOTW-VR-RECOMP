#!/usr/bin/env python3
"""The runes aimed by hand, in the game against fake_xr (runtime/nvn/vulkan/exec.c rune_pick_aim).

While a rune is aimed (L held), the game reads its G-buffer at one point of the picture to pick Stasis', Magnesis'
and Cryonis' target. With the option on (the default) that point is where the right hand points: fake_xr's right
hand, the head held still, points ahead, 35 degrees up and 35 degrees down in turn, and the pick's point and what it
read back (its third target: the depth there, 1.0 the sky) follow it. In stereo each eye's picture is off-centre, so
each eye has its own point for the same ray. SAVAGEWIND_VR_RUNE_AIM=head: the eye's own axis (the picture's centre in
mono, BetterVR's fix in stereo), whatever the hand does. Aimed by hand, the ray is drawn as dots (the bow arc's).

  python tools/vr/test_vr_rune_aim.py --save <scratch save> [--out build/vr/rune_aim] [--stereo]
"""
import argparse
import os
import re
import struct
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


def run(save, out, env, seconds=14.0):
    game, proc, log = re_run.boot(save, out, env, script())
    samples, aims, dots = [], 0, 0
    try:
        game.cmd('hold', 'l', ok=False)
        time.sleep(3.0)
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            time.sleep(0.5)
            text = open(os.path.join(out, 'game.log'), encoding='utf-8', errors='replace').read()
            picks = re.findall(r'\[vr-rune\] pick at ([\d.]+) ([\d.]+) .* targets \w+ \w+ (\w+)', text)
            if not picks:
                continue
            u, v, depth_at = float(picks[-1][0]), float(picks[-1][1]), int(picks[-1][2], 16)
            d = game.cmd('mem', 'read', '%#x' % depth_at, '4', 'u32', ok=False)
            depth = struct.unpack('<f', struct.pack('<I', int(d.get('value.0', '0'), 0) & 0xffffffff))[0]
            samples.append((u, v, depth))
        v = game.cmd('vr', ok=False)
        aims, dots = int(v.get('rune_aims', 0)), int(v.get('arc_frames', 0))
        game.cmd('shot', os.path.relpath(os.path.join(os.path.abspath(out), 'aim.png'), re_run.T.TREE), ok=False)
    finally:
        game.cmd('release', 'l', ok=False)
        perf_routes.stop_game(game, proc, log)
    return samples, aims, dots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/rune_aim')
    ap.add_argument('--stereo', action='store_true')
    a = ap.parse_args()
    base = {'SAVAGEWIND_VR_LOG_RUNE_AIM': '1', 'SAVAGEWIND_VR_MOTION': '0'}
    if a.stereo:
        base['SAVAGEWIND_VR_STEREO'] = '1'
    ok = True

    def check(cond, what):
        nonlocal ok
        print('  %s   %s' % ('ok' if cond else 'FAIL', what))
        ok = ok and cond

    print('== hand')
    s, aims, dots = run(a.save, os.path.join(a.out, 'hand'), base)
    for u, v, depth in s:
        print('    pick %.3f %.3f depth %.4f' % (u, v, depth))
    vs = sorted(set(round(x[1], 2) for x in s))
    # the three ways the hand points, as each eye sees them: the pick's v in three bands (up, ahead, down)
    up = [x for x in s if x[1] < vs[0] + 0.05] if vs else []
    down = [x for x in s if x[1] > vs[-1] - 0.05] if vs else []
    mid = [x for x in s if x not in up and x not in down]
    check(aims > 0, 'the pick was set by VR (%d draws)' % aims)
    check(bool(up) and bool(mid) and bool(down) and vs[-1] - vs[0] > 0.4,
          'the pick followed the hand up, ahead and down (v %s)' % ' '.join('%.2f' % v for v in vs))
    check(bool(s) and all(0.3 < x[0] < 0.7 for x in s), 'across, it stayed near the middle (the hand points ahead)')
    check(bool(up) and all(x[2] >= 0.9999 for x in up), 'pointing up it read the sky (depth 1.0)')
    check(bool(down) and all(x[2] < 0.999 for x in down), 'pointing down it read the ground (nearer)')
    check(dots > 0, "the hand's ray drawn as dots on the eyes' pictures (%d pictures)" % dots)
    print('== head (SAVAGEWIND_VR_RUNE_AIM=head)')
    env = dict(base)
    env['SAVAGEWIND_VR_RUNE_AIM'] = 'head'
    s, aims, dots = run(a.save, os.path.join(a.out, 'head'), env, seconds=8.0)
    for u, v, depth in s:
        print('    pick %.3f %.3f depth %.4f' % (u, v, depth))
    check(aims > 0, 'the pick was set by VR (%d draws)' % aims)
    check(dots == 0, "no ray drawn (%d pictures)" % dots)
    if a.stereo:
        check(bool(s) and len(set((round(x[0], 2), round(x[1], 2)) for x in s)) <= 2,
              "the eye's axis: one point an eye, the hand not followed")
    else:
        check(all(abs(x[0] - 0.5) < 0.005 and abs(x[1] - 0.5) < 0.005 for x in s),
              "mono: the picture's centre, the game's own (%d moves)" % len(s))
    print('all passed' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
