#!/usr/bin/env python3
"""(play, not a pass/fail test) Swimming and the paraglider in VR against fake_xr, at Zora's Domain: teleports around
until the player's movement flags say swimming (1 << 10), swims with the stick, then from 40 m up jumps and opens the
paraglider (1 << 15). Prints the flags, the eye's height and how far Link swam; pictures in build/vr/play_water.

  python tools/vr/play_water.py <scratch save>
"""
import json, math, os, sys, time
sys.path.insert(0, os.path.abspath('tools/vr'))
import handsim

out = os.path.abspath('build/vr/play_water')
sim = handsim.Sim(sys.argv[1], out, {'SAVAGEWIND_TEST_WARP': '3315.61,255.64,-501.00',
                                                'SAVAGEWIND_VR_STEREO': '1', 'SAVAGEWIND_VR_LOG_ARMS': '60'})
g = sim.game
vr = lambda: g.cmd('vr', ok=False, timeout=60)  # noqa: E731
flags = lambda: int(vr().get('move_flags', -1))   # noqa: E731
try:
    r = sim.run
    r('pose ahead'); time.sleep(3)
    p0 = g.cmd('pos', ok=False)
    print('start', p0.get('x'), p0.get('y'), p0.get('z'), 'flags %x' % flags(), flush=True)
    r('shot 0_start')
    print('give glider', json.dumps(g.cmd('give', 'paraglider', ok=False, timeout=60))[:400], flush=True)
    print('give stole', json.dumps(g.cmd('give', 'PlayerStole', ok=False, timeout=60))[:400], flush=True)
    swim = None
    for k in range(24):
        a = math.radians(k * 45)
        d = 15 + 15 * (k // 8)
        x, z = p0['x'] + d * math.sin(a), p0['z'] + d * math.cos(a)
        g.cmd('teleport', '%.1f' % x, '%.1f' % (p0['y'] + 3), '%.1f' % z, ok=False, timeout=60)
        time.sleep(3)
        f = flags()
        p = g.cmd('pos', ok=False)
        print('try', k, '%.1f %.1f %.1f' % (p['x'], p['y'], p['z']), 'flags %x' % f, flush=True)
        if f > 0 and f & (1 << 10):
            swim = (x, z)
            break
    if swim:
        r('shot 1_swimming'); r('xshot 1_swimeye')
        v = vr(); print('swim eye_height', v.get('eye_height'), flush=True)
        q0 = g.cmd('pos', ok=False)
        r('stick left 0 1'); time.sleep(3); r('stick left 0 0')
        q1 = g.cmd('pos', ok=False)
        print('swam', round(math.hypot(q1['x'] - q0['x'], q1['z'] - q0['z']), 2), 'm, flags %x' % flags(), flush=True)
        r('shot 2_swam')
        print('arms', sim.arms(), flush=True)
    # the glider: high up, jump, X again in the air
    g.cmd('teleport', '%.1f' % p0['x'], '%.1f' % (p0['y'] + 40), '%.1f' % p0['z'], ok=False, timeout=60)
    time.sleep(0.8)
    B = '/user/hand/right/input/b/click'
    for i in range(3):
        r('button %s 1' % B); time.sleep(0.15); r('button %s 0' % B); time.sleep(0.5)
    f = flags(); print('in the air flags %x' % f, flush=True)
    r('shot 3_air'); r('xshot 3_aireye')
    v = vr(); print('air eye_height', v.get('eye_height'), flush=True)
    time.sleep(3)
    print('landed flags %x' % flags(), flush=True)
finally:
    sim.stop()
