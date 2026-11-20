#!/usr/bin/env python3
"""(play, not a pass/fail test) Mount a wild horse near the Dueling Peaks stable in VR against fake_xr, with the hand
simulator, and ride it: the stick walks it, the right A spurs, the left grip brakes (BetterVR 1.0.1), a pat on the
neck pets it. Wild horses flee: it teleports Link crouched behind the nearest free one (from its last motion) and
presses A until the player's movement flags say "on a horse" (1 << 20), soothing with L when it bucks. Mounting can
take up to ~30 tries. Prints what it measured; pictures in --out.

  python tools/vr/play_horse.py <scratch save>
"""
import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath('tools/vr'))
import handsim

out = os.path.abspath('build/vr/play_horse')
env = {'SAVAGEWIND_TEST_WARP': '1745.37,115.57,1922.61', 'SAVAGEWIND_VR_LOG_MODELS': 'Horse_Link',
       'SAVAGEWIND_VR_STEREO': '1', 'SAVAGEWIND_VR_TRACE_GESTURES': '1'}
sim = handsim.Sim(sys.argv[1], out, env)
g = sim.game


def horses():
    text = open(os.path.join(out, 'game.log'), 'rb').read()[-400000:].decode('utf-8', 'replace')
    last = {}
    for m in re.finditer(r'^\[vr-model\] \d+ Horse_Link (\S+) (\S+) (\S+) (\S+)$', text, re.M):
        last[m.group(1)] = tuple(float(x) for x in m.group(2, 3, 4))
    return last


def flags():
    return int(g.cmd('vr', ok=False, timeout=60).get('move_flags', -1))


try:
    sim.run('pose ahead')
    time.sleep(2)
    print('horses', horses(), flush=True)
    riding = False
    g.cmd('press', 'lstick', '4', ok=False)   # (crouched: sneaking up on a wild horse)
    time.sleep(1)
    for attempt in range(45):
        h1 = {k: v for k, v in horses().items() if not (1750 < v[0] < 1760 and 1934 < v[2] < 1946) and not (1765 < v[0] < 1780 and v[2] < 1925)}
        time.sleep(0.4)
        h2 = horses()
        if not h1:
            print('no free horse', flush=True); break
        p = g.cmd('pos', ok=False)
        key = min(h1, key=lambda k: (h1[k][0] - p['x']) ** 2 + (h1[k][2] - p['z']) ** 2)
        a, b = h1[key], h2.get(key, h1[key])
        vx, vz = b[0] - a[0], b[2] - a[2]
        n = math.hypot(vx, vz)
        ang = math.atan2(vx, vz) if n > 0.05 else math.radians(attempt * 45)
        tx, tz = b[0] - 1.1 * math.sin(ang), b[2] - 1.1 * math.cos(ang)
        g.cmd('teleport', '%.2f' % tx, '%.2f' % (b[1] + 0.3), '%.2f' % tz, ok=False, timeout=60)
        time.sleep(0.6)
        g.cmd('look', '%.1f' % math.degrees(ang), '-10', ok=False, timeout=60)
        time.sleep(0.4)
        g.cmd('press', 'a', '6', ok=False)
        time.sleep(2.5)
        f = flags()
        print('attempt', attempt, key, 'horse', b, 'moving %.2f m' % n, 'flags %x' % f, flush=True)
        if f >= 0 and f & (1 << 20):
            riding = True
            break
        if f == 0x80000000:   # (on the horse? a wild one bucks: soothe it with L)
            sim.run('shot taming_%d' % attempt)
            for k in range(14):
                g.cmd('press', 'l', '4', ok=False)
                time.sleep(0.35)
                f = flags()
                print('  soothe', k, 'flags %x' % f, flush=True)
                if f & (1 << 20):
                    break
            sim.run('shot after_soothe_%d' % attempt)
            if f & (1 << 20):
                riding = True
                break
        if not f & 4:
            g.cmd('press', 'lstick', '4', ok=False); time.sleep(0.6)
    print('riding', riding, flush=True)
    if riding:
        import test_vr_game as T
        sim.run('shot ride0')
        sim.run('xshot ride0eye')
        for k in range(3):
            g.cmd('press', 'l', '4', ok=False)
            pp = g.cmd('pos', ok=False); cam = T.camera(g); hs = horses(); vv = g.cmd('vr', ok=False, timeout=60)
            near = min(hs.values(), key=lambda v: (v[0] - pp['x']) ** 2 + (v[2] - pp['z']) ** 2)
            print('DIAG pos', pp.get('x'), pp.get('y'), pp.get('z'), '| eye', cam, '| horse', near,
                  '| eye_height', vv.get('eye_height'), 'flags %x' % int(vv.get('move_flags', -1)), flush=True)
            time.sleep(0.7)
        sim.run('shot mounted')
        # pets first, while it is calm: an empty left hand patting low ahead (the horse's neck)
        for k in range(3):
            sim.run('move left -0.1 0.95 -0.45 0 -20 0 0.12')
            sim.run('move left -0.1 1.2 -0.4 0 0 0 0.2')
        time.sleep(1)
        text = open(os.path.join(out, 'game.log'), 'rb').read().decode('utf-8', 'replace')
        print('pats seen', text.count('[vr] riding: L (pet the horse)'), 'flags %x' % flags(), flush=True)
        sim.run('shot pat')
        sim.run('xshot mounted_eye')
        p0 = g.cmd('pos', ok=False)
        A = '/user/hand/right/input/a/click'
        sim.run('stick left 0 1')                 # walk the horse
        time.sleep(3)
        p1 = g.cmd('pos', ok=False)
        print('walked', round(math.hypot(p1['x'] - p0['x'], p1['z'] - p0['z']), 2), flush=True)
        sim.run('button %s 1' % A)                # spur (right A on a horse)
        time.sleep(0.3)
        sim.run('button %s 0' % A)
        time.sleep(2)
        p2 = g.cmd('pos', ok=False)
        print('after spur', round(math.hypot(p2['x'] - p1['x'], p2['z'] - p1['z']), 2), flush=True)
        sim.run('shot galloping')
        sim.run('stick left 0 0')
        sim.run('grip left 1')                   # brake (left grip on a horse)
        time.sleep(0.8)
        sim.run('grip left 0')
        p3 = g.cmd('pos', ok=False)
        time.sleep(1)
        p4 = g.cmd('pos', ok=False)
        print('speed after brake', round(math.hypot(p4['x'] - p3['x'], p4['z'] - p3['z']), 2), 'm/s', flush=True)
        sim.run('move left -0.1 0.95 -0.45 0 -20 0 0.15')   # a pat on the neck
        sim.run('move left -0.1 1.2 -0.4 0 0 0 0.15')
        sim.run('move left -0.1 0.95 -0.45 0 -20 0 0.15')
        time.sleep(1)
        sim.run('shot pat')
        print('vr', {k: v for k, v in g.cmd('vr', ok=False, timeout=60).items()
                     if k in ('move_flags', 'eye_height', 'world_view', 'controller_buttons')}, flush=True)
        g.cmd('press', 'b', '6', ok=False)       # get off
        time.sleep(2)
        print('after B flags %x' % flags(), flush=True)
finally:
    sim.stop()
