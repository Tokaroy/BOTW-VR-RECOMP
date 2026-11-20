#!/usr/bin/env python3
"""(play, not a pass/fail test) Magnesis by hand in VR against fake_xr: the sword drawn and dropped (the right waist
gesture), Magnesis chosen from the rune menu (left Y held, right stick left), used (left Y tap), the right hand aimed
at the dropped weapon (its place read from SAVAGEWIND_VR_LOG_MODELS), grabbed (right trigger) and raised (the right
grip held, the hand up: the stick's push). Prints where the weapon was before and after the lift.

  python tools/vr/play_magnesis.py <scratch save>
"""
import math, os, re, sys, time
sys.path.insert(0, os.path.abspath('tools/vr'))
import handsim

out = os.path.abspath('build/vr/play_magnesis')
sim = handsim.Sim(sys.argv[1], out, {'SAVAGEWIND_VR_STEREO': '1', 'SAVAGEWIND_VR_TRACE_GESTURES': '1',
                                                'SAVAGEWIND_VR_LOG_MODELS': 'Weapon_Lsword'})
g = sim.game
Y = '/user/hand/left/input/y/click'
vr = lambda: g.cmd('vr', ok=False, timeout=60)  # noqa: E731


def weapon():
    text = open(os.path.join(out, 'game.log'), 'rb').read()[-300000:].decode('utf-8', 'replace')
    m = re.findall(r'^\[vr-model\] \d+ Weapon_Lsword\S* \S+ (\S+) (\S+) (\S+)$', text, re.M)
    return tuple(float(x) for x in m[-1]) if m else None


try:
    r = sim.run
    r('pose ahead'); time.sleep(2)
    r('hand left -0.25 1.0 -0.2 0 -30 0')
    r('draw'); time.sleep(1)
    r('move right 0.25 1.0 0.05 0 0 0 0.4')                      # drop: right waist, grip held
    r('grip right 1'); time.sleep(2.0); r('grip right 0')
    r('move right 0.2 1.35 -0.4 0 0 0 0.4'); time.sleep(1.5)
    print('dropped at', weapon(), flush=True)
    r('stick left 0 -1'); time.sleep(0.8); r('stick left 0 0'); time.sleep(1)   # step back from it
    r('button %s 1' % Y); time.sleep(1.0)                         # the rune menu: Magnesis
    r('stick right -1 0'); time.sleep(0.6); r('stick right 0 0')
    r('button %s 0' % Y); time.sleep(1.5)
    r('button %s 1' % Y); time.sleep(0.15); r('button %s 0' % Y); time.sleep(1.5)   # use it (L)
    # aim the hand at the weapon: its way from the eye, in the game's world, as a yaw / pitch relative to the view
    w = weapon(); p = g.cmd('pos', ok=False); cam = g.cmd('camera', ok=False)
    dx, dy, dz = w[0] - cam['x'], w[1] - cam['y'], w[2] - cam['z']
    yaw = math.degrees(math.atan2(dx, dz)) - cam['yaw']
    pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    print('weapon', w, 'eye', cam['x'], cam['y'], cam['z'], 'aim yaw %.1f pitch %.1f' % (yaw, pitch), flush=True)
    r('head 0 1.66 -0.03 %.1f %.1f 0' % (-yaw, max(pitch, -60)))
    r('hand right 0.2 1.35 -0.4 %.1f %.1f 0' % (-yaw, pitch)); time.sleep(1)
    r('shot 3_aim'); r('xshot 3_aimeye')
    y0 = weapon()
    r('tap trigger right'); time.sleep(1.5)                       # grab (A)
    r('shot 4_grabbed')
    r('grip right 1'); time.sleep(0.3)                            # steer: grip held, hand raised
    r('move right 0.2 1.6 -0.4 %.1f %.1f 0 0.6' % (-yaw, pitch)); time.sleep(2)
    y1 = weapon()
    r('shot 5_lifted'); r('xshot 5_liftedeye')
    print('weapon before %s after lift %s' % (y0, y1), flush=True)
    v = vr(); print('vr', {k: v.get(k) for k in ('rune_aims', 'controller_ry', 'controller_buttons')}, flush=True)
    r('move right 0.2 1.35 -0.4 0 0 0 0.6'); r('grip right 0'); time.sleep(0.5)
    r('tap trigger right'); time.sleep(1)
finally:
    sim.stop()
