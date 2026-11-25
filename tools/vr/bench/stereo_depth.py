#!/usr/bin/env python3
"""Stereo depth against fake_xr (docs/vr/PERFORMANCE.md, "Checking the picture"): Link's hands held ahead (0.53 m
from the eyes), three captures of both eyes, and for each patch the shift between the eyes and the depth it gives.
With fake_xr's asymmetric fields (left eye -0.942 / +0.698 rad) a point at infinity shifts by INF px between the
captures; a patch's disparity = its shift - INF, its depth = 0.063 m x FOCAL / disparity. Right numbers: the hands
~0.54 m, the far mountains ~0 px (a few px: they are not at infinity).

  python tools/vr/bench/stereo_depth.py --case base --exe build/savagewind.exe --save <scratch save>
        [--yaw 37] [--spin] [--walk] [--patches 880,1150,50 640,430,40] [--env K=V ...]
  python tools/vr/bench/stereo_depth.py --only <run dir>      (measure captures already made)

--yaw turns the head (cameras along the world's axes hide errors: identity matrices look like them); --spin turns
with the right stick while shooting, --walk walks with the left one. Side-by-side PNGs h0..h2.png in the run folder.
"""
import argparse
import glob
import math
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

W = 1718                      # fake_xr's eye image width at SAVAGEWIND_VR_HEIGHT=1800
TL, TR = math.tan(0.942), math.tan(0.698)
FOCAL = W / (TL + TR)
INF = (TL - TR) * FOCAL       # the left eye's centre is TL*F from its left edge, the right eye's TR*F
IPD = 0.063
HANDS = ['hand left -0.20 1.35 -0.40 0 0 0', 'hand right 0.20 1.35 -0.40 0 0 0']


def load(p):
    return np.asarray(Image.open(p).convert('L'), dtype=np.float32)


def disparity(cap, tag, x, y, s):
    l = load(glob.glob(os.path.join(cap, tag + '_layer0_view0.ppm'))[0])
    r = load(glob.glob(os.path.join(cap, tag + '_layer0_view1.ppm'))[0])
    p = l[y - s:y + s, x - s:x + s]
    p = p - p.mean()
    best = None
    for dx in range(0, 700):
        xx = x - dx
        if xx - s < 0:
            break
        for dy in (-2, -1, 0, 1, 2):
            q = r[y + dy - s:y + dy + s, xx - s:xx + s]
            q = q - q.mean()
            c = float((p * q).sum() / (np.sqrt((p * p).sum() * (q * q).sum()) + 1e-6))
            if best is None or c > best[0]:
                best = (c, dx, dy)
    c, dx, dy = best
    d = dx - INF
    return dx, dy, c, d, (IPD * FOCAL / d if d > 0 else float('inf'))


def measure(run_dir, patches):
    cap = os.path.join(run_dir, 'cap')
    for k in range(3):
        L = glob.glob(os.path.join(cap, 'h%d_layer0_view0.ppm' % k))
        R = glob.glob(os.path.join(cap, 'h%d_layer0_view1.ppm' % k))
        if not (L and R):
            print('h%d: no capture' % k)
            continue
        l, r = load(L[0]), load(R[0])
        Image.fromarray(np.hstack([l, r]).astype(np.uint8)).resize((1718, 900)).save(os.path.join(run_dir, 'h%d.png' % k))
        print('h%d mean brightness: left %.0f right %.0f' % (k, l.mean(), r.mean()))
        for spec in patches:
            v = [int(t) for t in spec.split(',')]
            dx, dy, c, d, depth = disparity(cap, 'h%d' % k, v[0], v[1], v[2] if len(v) > 2 else 40)
            print('  patch %4d,%4d: shift %3d px (dy %d, corr %.2f) -> disparity %.1f px -> %.2f m' % (v[0], v[1], dx, dy, c, d, depth))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only')
    ap.add_argument('--case', default='depth')
    ap.add_argument('--yaw', type=int, default=0)
    ap.add_argument('--spin', action='store_true')
    ap.add_argument('--walk', action='store_true')
    ap.add_argument('--patches', nargs='*', default=['880,1150,50', '1360,1170,50', '640,430,40'])
    if '--only' in sys.argv:
        a, _ = ap.parse_known_args()
        measure(a.only, a.patches)
        return
    import common
    common.add_args(ap, port=8900)
    a = ap.parse_args()
    run_dir = os.path.join(a.out, a.case)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    live = os.path.join(run_dir, 'live.txt')
    open(live, 'w').write('seq 0\n')
    game, proc, log = common.launch(a, run_dir, live=live, hz='90', extra_env=['SAVAGEWIND_VR_LOG_ARMS=30'])
    try:
        common.ready(game, proc, 300, 8)
        open(live, 'w').write('\n'.join(['seq 1', 'head 0 1.7 0 %d -20 0' % a.yaw] + HANDS) + '\n')
        time.sleep(6)
        for k in range(3):
            extra = (['stick /user/hand/left/input/thumbstick 0 1'] if a.walk else []) + \
                    (['stick /user/hand/right/input/thumbstick 1 0'] if a.spin else [])
            head = 'head 0 1.7 0 %d -20 0' % (a.yaw + (180 if a.walk else 0))
            open(live, 'w').write('\n'.join(['seq %d' % (10 * k + 2), head] + HANDS + extra) + '\n')
            time.sleep(1.5)
            # (each capture stalls the game for seconds: well apart)
            open(live, 'w').write('\n'.join(['seq %d' % (10 * k + 3), head] + HANDS + extra + ['shot h%d' % k]) + '\n')
            time.sleep(8)
            open(live, 'w').write('\n'.join(['seq %d' % (10 * k + 4), head] + HANDS + [
                'stick /user/hand/left/input/thumbstick 0 0', 'stick /user/hand/right/input/thumbstick 0 0']) + '\n')
            time.sleep(1)
    finally:
        common.stop(game, proc, log)
    measure(run_dir, a.patches)


if __name__ == '__main__':
    main()
