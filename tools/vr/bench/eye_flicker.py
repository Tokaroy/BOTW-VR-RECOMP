#!/usr/bin/env python3
"""Each eye's picture over consecutive frames with the head still (docs/vr/PERFORMANCE.md): flicker in one eye, an eye
that sometimes gets the other eye's picture, or eyes that differ. --frames consecutive frames of both eyes are captured
(fake_xr `shot <tag> <n>`) a few times; per eye, the share of pixels that change by more than --level grey levels from
one frame to the next (a still scene: only wind, water, particles should move), and per frame the far patch's shift
between the eyes (a frame whose shift jumps had an eye's picture from the other eye or from another moment).

  python tools/vr/bench/eye_flicker.py --case mv --exe build/savagewind.exe --save <scratch save>
        [--ini "antialias = off" "vr_render_mode = 2" "vr_experimental = 1"] [--env K=V ...] [--yaw 37] [--frames 6]
"""
import argparse
import glob
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import stereo_depth as sd  # noqa: E402


def load(p):
    return np.asarray(Image.open(p).convert('L'), dtype=np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common.add_args(ap, port=8950)
    ap.add_argument('--case', default='flicker')
    ap.add_argument('--yaw', type=int, default=37)
    ap.add_argument('--frames', type=int, default=6)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--level', type=float, default=12)
    ap.add_argument('--patch', default='640,430,40', help='a far patch x,y,size in the left picture (its shift between eyes)')
    a = ap.parse_args()
    run_dir = os.path.join(a.out, a.case)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    live = os.path.join(run_dir, 'live.txt')
    open(live, 'w').write('seq 0\n')
    game, proc, log = common.launch(a, run_dir, live=live, hz='90')
    try:
        common.ready(game, proc, 300, 8)
        open(live, 'w').write('seq 1\nhead 0 1.7 0 %d -10 0\n' % a.yaw)
        time.sleep(6)
        for k in range(a.rounds):
            open(live, 'w').write('seq %d\nhead 0 1.7 0 %d -10 0\nshot f%d %d\n' % (10 * k + 2, a.yaw, k, a.frames))
            time.sleep(10)
    finally:
        common.stop(game, proc, log)
    px, py, ps = [int(v) for v in a.patch.split(',')]
    cap = os.path.join(run_dir, 'cap')
    tot = {0: [], 1: []}
    for k in range(a.rounds):
        frames = []
        for i in range(a.frames):
            L = glob.glob(os.path.join(cap, 'f%d_%d_layer0_view0.ppm' % (k, i)))
            R = glob.glob(os.path.join(cap, 'f%d_%d_layer0_view1.ppm' % (k, i)))
            if L and R:
                frames.append((L[0], R[0]))
        if len(frames) < 2:
            print('round %d: %d frames captured' % (k, len(frames)))
            continue
        shifts = []
        for i, (L, R) in enumerate(frames):
            dx, dy, c, d, depth = sd.disparity(os.path.dirname(L), os.path.basename(L).replace('_layer0_view0.ppm', ''), px, py, ps)
            shifts.append('%d(%.2f)' % (dx, c))
        for e in (0, 1):
            ch = []
            for i in range(1, len(frames)):
                x, y = load(frames[i - 1][e]), load(frames[i][e])
                ch.append(100 * float((np.abs(x - y) > a.level).mean()))
            tot[e] += ch
            print('round %d %s eye: changed %s %%' % (k, 'left' if e == 0 else 'right', ' '.join('%.2f' % v for v in ch)))
        print('round %d far-patch shift per frame (px, corr): %s' % (k, ' '.join(shifts)))
        if k == 0:
            l0, r0 = load(frames[0][0]), load(frames[0][1])
            Image.fromarray(np.hstack([l0, r0]).astype(np.uint8)).resize((1718, 900)).save(os.path.join(run_dir, 'eyes.png'))
    for e in (0, 1):
        if tot[e]:
            print('%s eye: mean %.2f%%, max %.2f%% of pixels changed frame to frame' %
                  ('left' if e == 0 else 'right', float(np.mean(tot[e])), float(np.max(tot[e]))))


if __name__ == '__main__':
    main()
