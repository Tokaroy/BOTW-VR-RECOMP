#!/usr/bin/env python3
"""(play, not a pass/fail test) The body gestures not played elsewhere, in VR against fake_xr with the hand simulator:
the whistle (both grips with the hands cupped at the mouth), the quick menu (a grip held over the right shoulder) and
the throw (the right trigger held over the right shoulder with the sword out, a swing ahead, let go). Prints the
controller buttons seen while whistling, the screens opened by the grip held and where the sword went when thrown;
pictures in build/vr/play_misc.

  python tools/vr/play_misc.py <scratch save>
"""
import math
import os
import re
import sys
import time

sys.path.insert(0, os.path.abspath('tools/vr'))
import handsim

out = os.path.abspath('build/vr/play_misc')
sim = handsim.Sim(sys.argv[1], out, {'SAVAGEWIND_VR_STEREO': '1', 'SAVAGEWIND_VR_TRACE_GESTURES': '1',
                                     'SAVAGEWIND_VR_LOG_MODELS': 'Weapon_Lsword', 'SAVAGEWIND_LOG_SCREENS': '1'})
g = sim.game


def log_tail(n=400000):
    return open(os.path.join(out, 'game.log'), 'rb').read()[-n:].decode('utf-8', 'replace')


def weapon():
    m = re.findall(r'^\[vr-model\] \d+ Weapon_Lsword\S* \S+ (\S+) (\S+) (\S+)$', log_tail(), re.M)
    return tuple(float(x) for x in m[-1]) if m else None


def vr():
    return g.cmd('vr', ok=False, timeout=60)


try:
    r = sim.run
    r('pose ahead'); time.sleep(2)
    p = g.cmd('pos', ok=False)
    print('start', p.get('x'), p.get('y'), p.get('z'), flush=True)

    # the whistle: both hands cupped at the mouth (a little below and ahead of the eyes), both grips held
    r('move left -0.03 1.56 -0.13 0 0 0 0.4'); r('move right 0.03 1.56 -0.13 0 0 0 0.4')
    r('grip left 1'); r('grip right 1'); time.sleep(0.3)
    v = vr()
    print('whistle buttons', v.get('controller_buttons'), flush=True)
    r('shot 1_whistle'); time.sleep(1.2)
    r('shot 1_whistle_late')
    r('grip left 0'); r('grip right 0')
    r('pose ahead'); time.sleep(1.5)

    # the quick menu: the right hand over the right shoulder, the grip held (no weapon out: the weapons' menu)
    n0 = len(log_tail())
    r('move right 0.15 1.65 0.12 0 0 0 0.4')
    r('grip right 1'); time.sleep(1.2)
    r('shot 2_quickmenu'); r('xshot 2_quickmenu_eye')
    r('stick right 1 0'); time.sleep(0.4); r('stick right 0 0'); time.sleep(0.4)
    r('grip right 0'); time.sleep(1.5)
    text = log_tail()
    print('screens', re.findall(r'^\[screens\].*$', text[min(n0, len(text)):], re.M)[-4:], flush=True)
    r('move right 0.20 1.35 -0.40 0 0 0 0.4'); time.sleep(1)
    r('shot 2_after_quickmenu')

    # the throw: the sword out, the right trigger held over the right shoulder, a swing ahead, let go
    if vr().get('held') in (None, 0, 'none'):
        r('draw')
    time.sleep(1)
    w0 = weapon()
    print('sword before', w0, flush=True)
    r('move right 0.15 1.65 0.12 0 0 0 0.4')
    r('trigger right 1'); time.sleep(0.8)
    r('shot 3_aim_throw')
    r('move right 0.25 1.55 -0.55 0 -10 0 0.15')
    r('trigger right 0'); time.sleep(2.5)
    w1 = weapon()
    r('shot 3_thrown')
    d = math.dist(w0, w1) if w0 and w1 else None
    print('sword after', w1, 'moved', None if d is None else round(d, 2), 'm', flush=True)
    print('held lines', re.findall(r'^\[vr\] gesture.*$', log_tail(60000), re.M)[-6:], flush=True)
finally:
    sim.stop()
