#!/usr/bin/env python3
"""One boot per rendering mode, a few minutes each (docs/vr/PERFORMANCE.md): speed and the checks that catch a broken
picture, against fake_xr with the eyes 0 m apart (FAKE_XR_IPD=0: both pictures must be the same one).

  1. speed: --measure seconds standing at the Great Plateau (as bench.py): headset fps, a pair's p95, the GPU's use;
  2. the eyes alike: the head at two yaws, both eyes captured: the part of the common field differing by more than 24
     grey levels (something drawn in one eye only), and the left eye kept as this run's picture (ref_<yaw>.png);
  3. turning with the stick: both eyes captured mid-turn, the sideways shift between them (0: one moment in both);
  4. a menu opened and closed: the frames right after, the same shift and differing part, and whether the view went
     back to the virtual screen after it closed (a flicker);
  5. --ref <run dir>: this run's pictures against another run's (the same place and hour): PSNR, the quality an
     option costs.

  python tools/vr/bench/quick.py --exe build/savagewind --save <scratch save> --case stereo --out build/vr/quick
        [--env SAVAGEWIND_VR_RENDER=multiview SAVAGEWIND_VR_EXPERIMENTAL=1] [--ini 'grass = 0'] [--ref <run dir>]
Prints RESULT {json}; also <out>/<case>/result.json.
"""
import argparse
import json
import os
import re
import shutil
import statistics
import sys
import threading
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import bench  # noqa: E402

R = '/user/hand/right/input/thumbstick'
STEP = 0.004
YAWS = (0, 135)


def grid(path, fov, span=0.55):
    im = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)
    h, w = im.shape[:2]
    tl, tr, tu, td = (np.tan(f) for f in fov)
    t = np.arange(-span, span, STEP)
    px = ((t - tl) / (tr - tl) * w).astype(int).clip(0, w - 1)
    py = ((tu - t[::-1]) / (tu - td) * h).astype(int).clip(0, h - 1)
    return im[py][:, px]


def eyes(a, b, level=24, max_dx=12):
    """(sideways shift of b against a, % of the field differing by more than level at shift 0)"""
    ga, gb = a.mean(axis=2), b.mean(axis=2)
    n, m = ga.shape[1], ga.shape[0]
    x0, x1, y0, y1 = n // 4, 3 * n // 4, m // 4, 3 * m // 4
    A = ga[y0:y1, x0:x1]
    sc = {dx: np.abs(A - gb[y0:y1, x0 + dx:x1 + dx]).mean() for dx in range(-max_dx, max_dx + 1)}
    dx = min(sc, key=sc.get)
    if sc[dx] >= sc[0] * 0.97:
        dx = 0
    return dx, round(100.0 * float((np.abs(a - b).max(axis=2) > level).mean()), 2)


def psnr(a, b):
    mse = float(((a - b) ** 2).mean())
    return round(99.0 if mse < 1e-6 else 10 * np.log10(255.0 ** 2 / mse), 2)


def main():
    ap = argparse.ArgumentParser()
    common.add_args(ap)
    ap.add_argument('--case', default='quick')
    ap.add_argument('--boot', type=float, default=300)
    ap.add_argument('--measure', type=float, default=15)
    ap.add_argument('--ref', help='another run dir: PSNR of this run\'s pictures against its')
    a = ap.parse_args()
    run_dir = os.path.join(os.path.abspath(a.out), a.case)
    shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir)
    live = os.path.join(run_dir, 'fake_xr_live.txt')
    game, proc, log = common.launch(a, run_dir, live=live, extra_env=['FAKE_XR_IPD=0', 'SAVAGEWIND_VR_ROOMSCALE=0'])
    seq = [0]

    def send(*lines):
        seq[0] += 1
        with open(live, 'w') as f:
            f.write('seq {}\n{}\n'.format(seq[0], '\n'.join(lines)))
        until = time.monotonic() + 10
        while time.monotonic() < until:
            try:
                with open(live + '.ack') as f:
                    if int(f.read().split()[0]) >= seq[0]:
                        return
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.03)

    def flog():
        try:
            return open(os.path.join(run_dir, 'fake_xr.log'), encoding='utf-8', errors='replace').read()
        except OSError:
            return ''

    def shot(tag, n=0, limit=120):
        send('stick {} {} 0'.format(R, 0.6 if tag.startswith(('turn', 'post')) else 0),
             'shot {} {}'.format(tag, n) if n else 'shot {}'.format(tag))
        want = 'capture %s_%d_' % (tag, n - 1) if n else 'capture %s_' % tag
        t0 = time.monotonic()
        while time.monotonic() - t0 < limit and want not in flog():
            time.sleep(0.3)

    res = {'case': a.case, 'env': a.env, 'ini': a.ini}
    t_boot = time.monotonic()
    alive = True
    try:
        common.ready(game, proc, a.boot)
        res['boot_s'] = round(time.monotonic() - t_boot)
        # 1. speed
        stop, gpu = threading.Event(), {}
        th = threading.Thread(target=bench.gpu_sampler, args=(stop, gpu), daemon=True)
        v0 = game.cmd('vr', ok=False, timeout=60); t0 = time.monotonic()
        th.start()
        time.sleep(a.measure)
        v1 = game.cmd('vr', ok=False, timeout=60); t1 = time.monotonic()
        stop.set(); th.join()
        pf = game.cmd('vr', 'frametimes', 10, ok=False, timeout=30)
        res['hmd_fps'] = round((v1['frames'] - v0['frames']) / (t1 - t0), 1)
        res['pair_p95_ms'] = pf.get('frame_ms_p95', 0) if isinstance(pf, dict) else 0
        res['gpu'] = round(max(statistics.mean(v) for v in gpu.values()), 0) if gpu else 0
        # 2. the eyes alike, two yaws
        for y in YAWS:
            send('stick {} 0 0'.format(R), 'head 0 1.7 0 {} -10 0'.format(y))
            time.sleep(1.5)
            shot('y%d' % y)
        send('head 0 1.7 0 0 -10 0')
        time.sleep(1)
        # 3. turning
        send('stick {} 0.6 0'.format(R))
        time.sleep(1.5)
        shot('turn')
        send('stick {} 0 0'.format(R))
        time.sleep(1)
        # 4. a menu, open and closed
        st = lambda: game.cmd('vr', ok=False, timeout=30)
        game.cmd('press', 'plus', ok=False)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 10 and st().get('world_view') is not False:
            time.sleep(0.1)
        res['menu_opened'] = st().get('world_view') is False
        time.sleep(1.5)
        send('stick {} 0 0'.format(R))   # (the ack's frame: now)
        f_close = int(open(live + '.ack').read().split()[1]) if os.path.exists(live + '.ack') else 0
        game.cmd('press', 'plus', ok=False)
        shot('post', 6)
        send('stick {} 0 0'.format(R))
        time.sleep(1)
        alive = proc.poll() is None
    finally:
        common.stop(game, proc, log)
    res['alive'] = alive
    gl = open(os.path.join(run_dir, 'game.log'), encoding='utf-8', errors='replace').read()
    m = re.search(r'^\[vr\] rendering: (.*)$', gl, re.M)
    res['rendering'] = m.group(1) if m else '?'
    res['freezes'] = len(common.freezes(run_dir))
    fl = flog()
    fov = dict((t, [float(x) for x in f]) for t, *f in re.findall(r'capture (\S+) fov (\S+) (\S+) (\S+) (\S+)', fl))
    cap = os.path.join(run_dir, 'cap')

    def pair(tag):
        lt = next((t for t in sorted(fov) if re.fullmatch(r'%s(_layer\d+)?_view0' % re.escape(tag), t)), None)
        if not lt:
            return None
        rt = lt[:-1] + '1'
        return grid(os.path.join(cap, lt + '.ppm'), fov[lt]), grid(os.path.join(cap, rt + '.ppm'), fov[rt])

    res['eyes'] = {}
    for y in YAWS:
        p = pair('y%d' % y)
        if p:
            e = eyes(*p)
            res['eyes']['y%d' % y] = e[1]
            res.setdefault('eyes_shift', {})['y%d' % y] = e[0]
            Image.fromarray(p[0].clip(0, 255).astype(np.uint8)).save(os.path.join(run_dir, 'ref_%d.png' % y))
            Image.fromarray(np.hstack([p[0], p[1], np.abs(p[0] - p[1]) * 4]).clip(0, 255).astype(np.uint8)).save(
                os.path.join(run_dir, 'eyes_%d.png' % y))
    p = pair('turn')
    res['turn'] = eyes(*p) if p else None
    post = []
    for i in range(6):
        p = pair('post_%d' % i)
        post.append(eyes(*p) if p else None)
    res['post_menu'] = post
    seqf = [(int(f), t) for f, t in re.findall(r'^frame (\d+) display_time \S+ layers \d+ (\S*)', fl, re.M)]
    runs = []
    for f, t in seqf:
        if f < f_close or f > f_close + 200:
            continue
        k = 'world' if t.startswith('projection') else 'screen' if t else 'empty'
        if runs and runs[-1][0] == k:
            runs[-1][1] += 1
        else:
            runs.append([k, 1])
    res['after_menu'] = ' '.join('%sx%d' % (k, n) for k, n in runs)
    if a.ref:
        res['psnr_vs_ref'] = {}
        for y in YAWS:
            mine, theirs = os.path.join(run_dir, 'ref_%d.png' % y), os.path.join(a.ref, 'ref_%d.png' % y)
            if os.path.exists(mine) and os.path.exists(theirs):
                A = np.asarray(Image.open(mine), dtype=np.float32)
                B = np.asarray(Image.open(theirs), dtype=np.float32)
                if A.shape == B.shape:
                    res['psnr_vs_ref']['y%d' % y] = psnr(A, B)
    # the verdict: what counts as broken
    bad = []
    if not alive:
        bad.append('the game stopped')
    if len(res['eyes']) < len(YAWS):
        bad.append('eyes not captured')
    # (Stereo's right eye is a later game frame: grass and leaves in the wind differ by 3-7% there; something drawn
    # in one eye only - smoke, a patch of ground, a marker - or a darker eye goes well past it)
    if any(v > 8.0 for v in res['eyes'].values()) or any(res.get('eyes_shift', {}).values()):
        bad.append('the eyes differ (%s)' % res['eyes'])
    if res['turn'] is None or res['turn'][0] != 0:
        bad.append('turning, the eyes apart (%s)' % (res['turn'],))
    got = [p for p in post if p]
    if not got or any(p[0] != 0 or p[1] > 10.0 for p in got):
        bad.append('after the menu, the eyes apart (%s)' % post)
    if sum(1 for k, n in runs if k != 'world') > 1 or not res.get('menu_opened'):
        bad.append('the menu: %s (opened %s)' % (res['after_menu'], res.get('menu_opened')))
    res['broken'] = bad
    json.dump(res, open(os.path.join(run_dir, 'result.json'), 'w'), indent=1)
    print('RESULT', json.dumps(res))


if __name__ == '__main__':
    main()
