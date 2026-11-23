#!/usr/bin/env python3
"""The arm rig (B10, docs/vr/FEATURES.md), against fake_xr with the hand simulator: the hands go through a set of poses
(ahead, overhead, out to the sides, across the chest, palms up and down, pointing up and down) and the right wrist is
turned from -150 to +150 deg about the controller's pointing line. Read from the arms' log line ([vr-arms]: the elbow
from the shoulder in Link's body's frame, down / out / back, the forearm's roll, the clavicle's turn) and pictures of
the eye's view. Passes when:
  - every pose is solved (the wrist on its controller within 2 cm),
  - turning the wrist moves the elbow little: under 6 cm from one 30 deg step to the next and 12 cm over the sweep
    (the first rig swung it round the arm),
  - the forearm's roll changes smoothly over the sweep (no step over 60 deg: it never flips at 180),
  - overhead the elbows may rise over the shoulders and the clavicles turn (the first rig kept them under).
SAVAGEWIND_VR_ARM_RIG=0 (--old) runs the first rig for comparison (it is expected to fail the wrist sweep).

  python tools/vr/test_vr_arm_rig.py --save <scratch save> [--out build/vr/arm_rig] [--old]
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handsim  # noqa: E402

POSES = ['quest_rest', 'ahead', 'hips', 'up', 'out', 'chest', 'palms_up', 'palms_down', 'point_up', 'point_down', 'shoulder']
NUM = r'(-?[\d.]+)'
LINE = re.compile(r'\[vr-arms\] left (ok|--) ' + NUM + r' m, right (ok|--) ' + NUM + r' m .*?forearm roll ' + NUM +
                  ' / ' + NUM + r'.*?elbow down/out/back ' + ' '.join([NUM] * 3) + ' / ' + ' '.join([NUM] * 3) +
                  r' m; clavicle ' + NUM + ' / ' + NUM)


def sample(sim, n=3):
    """the last arms line after the pose settled: (miss l, miss r, roll l, roll r, elbow l (d, o, b), elbow r, clav l, r)"""
    time.sleep(1.2 + 0.5 * n)
    lines = [l for l in open(os.path.join(sim.out, 'game.log'), errors='replace') if '[vr-arms]' in l]
    m = LINE.search(lines[-1]) if lines else None
    if not m:
        return None
    g = m.groups()
    f = [float(x) for i, x in enumerate(g) if i not in (0, 2)]
    return {'miss': (f[0], f[1]), 'roll': (f[2], f[3]), 'elbow': (tuple(f[4:7]), tuple(f[7:10])), 'clav': (f[10], f[11])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/arm_rig')
    ap.add_argument('--old', action='store_true', help='the first rig (SAVAGEWIND_VR_ARM_RIG=0)')
    a = ap.parse_args()
    env = {'SAVAGEWIND_VR_LOG_ARMS': '5', 'SAVAGEWIND_VR_STEREO': '0'}
    if a.old:
        env['SAVAGEWIND_VR_ARM_RIG'] = '0'
    sim = handsim.Sim(a.save, a.out, env)
    ok = True
    res = {}
    sweep = []

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    try:
        sim.run('head 0 1.7 0 0 0 0')
        sim.run('pose ahead')
        time.sleep(2)
        for p in POSES:
            sim.run('pose ' + p)
            r = sample(sim)
            res[p] = r
            sim.run('xshot pose_' + p)
            if r:
                print('  %-11s miss %.3f %.3f  roll %4.0f %4.0f  elbow L d/o/b %5.2f %5.2f %5.2f  R %5.2f %5.2f %5.2f  '
                      'clav %3.0f %3.0f' % ((p,) + r['miss'] + r['roll'] + r['elbow'][0] + r['elbow'][1] + r['clav']))
        # the right wrist turned about the pointing line, ahead
        sim.run('pose ahead')
        time.sleep(1)
        for ang in range(-150, 151, 30):
            sim.run('hand right 0.20 1.35 -0.40 0 0 %d' % ang)
            r = sample(sim, 2)
            sweep.append((ang, r))
            if r:
                print('  roll %+4d  right elbow d/o/b %5.2f %5.2f %5.2f  forearm roll %4.0f  miss %.3f' %
                      ((ang,) + r['elbow'][1] + (r['roll'][1], r['miss'][1])))
            if ang in (-150, 0, 150):
                sim.run('xshot roll_%+04d' % ang)
    finally:
        sim.stop()

    check(all(r is not None for r in res.values()), 'every pose read from the log')
    worst = max((max(r['miss']) for r in res.values() if r), default=9)
    check(worst < 0.02, 'every pose solved: the wrists on their controllers (worst %.3f m)' % worst)
    pts = [(ang, r['elbow'][1]) for ang, r in sweep if r]
    if len(pts) >= 2:
        step = max(sum((a - b) ** 2 for a, b in zip(pts[i][1], pts[i + 1][1])) ** 0.5 for i in range(len(pts) - 1))
        span = max(sum((a - b) ** 2 for a, b in zip(p[1], q[1])) ** 0.5 for p in pts for q in pts)
        check(step < 0.06, 'turning the wrist 30 deg moves the elbow under 6 cm (worst %.3f m)' % step)
        check(span < 0.12, 'over the whole -150..150 deg turn the elbow stays within 12 cm (%.3f m)' % span)
        rolls = [r['roll'][1] for _, r in sweep if r]
        jump = max(abs(rolls[i + 1] - rolls[i]) for i in range(len(rolls) - 1))
        check(jump <= 60, 'the forearm\'s roll changes smoothly, no flip (largest step %.0f deg)' % jump)
    else:
        check(False, 'the wrist sweep read from the log')
    up = res.get('up')
    if up:
        check(up['clav'][0] > 3 and up['clav'][1] > 3, 'hands overhead turn the clavicles (%.0f / %.0f deg)' % up['clav'])
        check(min(up['elbow'][0][0], up['elbow'][1][0]) < 0.10,
              'hands overhead: the elbows rise near or over the shoulders (down %.2f / %.2f m)' %
              (up['elbow'][0][0], up['elbow'][1][0]))
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
