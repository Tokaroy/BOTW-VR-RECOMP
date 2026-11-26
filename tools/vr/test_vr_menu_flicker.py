#!/usr/bin/env python3
"""After a menu closes, both eyes show one same world (a tester on 25.9: "in first person after opening menu or
inventory and closing there is flickering visible in main view (eye desynchronization)").

Against fake_xr with the eyes 0 m apart (FAKE_XR_IPD=0): the view turned with the right stick, both eyes captured for
several frames in a row before the menu (pre), right after it closes (post) and a few seconds later (late). Each frame's
two pictures, placed by the fields they were submitted with, must match: a sideways shift between them, or a part of
the picture that differs well beyond what the frames before the menu had, is one eye showing another moment (a stale
picture, the other eye's, the menu's). --menu plus (the inventory / pause menu) or minus (the map).

  python tools/vr/test_vr_menu_flicker.py --save <scratch save> [--mode compat|multiview|sync|mono] [--rounds 2]
        [--menu plus] [--out build/vr/menu_flicker]
"""
import argparse
import os
import re
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import perf_routes  # noqa: E402
import test_vr_game as T  # noqa: E402

R = '/user/hand/right/input/thumbstick'
MODES = {'compat': {'SAVAGEWIND_VR_RENDER': 'stereo'},
         'multiview': {'SAVAGEWIND_VR_RENDER': 'multiview', 'SAVAGEWIND_VR_EXPERIMENTAL': '1'},
         'sync': {'SAVAGEWIND_VR_RENDER': 'stereo', 'SAVAGEWIND_VR_SYNC': '1'},
         'mono': {'SAVAGEWIND_VR_RENDER': 'mono'}}
STEP = 0.004


def grid(path, fov, span=0.55):
    im = np.asarray(Image.open(path).convert('L'), dtype=np.float32)
    h, w = im.shape
    tl, tr, tu, td = (np.tan(f) for f in fov)
    t = np.arange(-span, span, STEP)
    px = ((t - tl) / (tr - tl) * w).astype(int).clip(0, w - 1)
    py = ((tu - t[::-1]) / (tu - td) * h).astype(int).clip(0, h - 1)
    return im[py][:, px]


def compare(a, b, level=24, max_dx=12):
    """(best dx, part differing at dx 0 in %, mean difference at dx 0)"""
    n = a.shape[1]
    m0, m1 = n // 4, 3 * n // 4
    ya, yb = a.shape[0] // 4, 3 * a.shape[0] // 4
    A = a[ya:yb, m0:m1]
    sc = {dx: np.abs(A - b[ya:yb, m0 + dx:m1 + dx]).mean() for dx in range(-max_dx, max_dx + 1)}
    dx = min(sc, key=sc.get)
    if sc[dx] >= sc[0] * 0.97:   # (no clearly better shift: flat ground, sky)
        dx = 0
    d = np.abs(a - b)
    return dx, 100.0 * (d > level).mean(), float(d.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--exe', default=T.EXE)
    ap.add_argument('--out', default='build/vr/menu_flicker')
    ap.add_argument('--mode', choices=sorted(MODES), default='compat')
    ap.add_argument('--menu', default='plus')
    ap.add_argument('--rounds', type=int, default=2)
    ap.add_argument('--post', type=int, default=40, help='frames captured right after the menu closes')
    ap.add_argument('--view', choices=['first', 'third'], default='first')
    a = ap.parse_args()
    T.EXE = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    live = os.path.join(out, 'fake_xr_live.txt')
    for p in (live, live + '.ack'):
        if os.path.exists(p):
            os.unlink(p)
    env = {'FAKE_XR_LIVE': live, 'FAKE_XR_IPD': '0', 'FAKE_XR_CAPTURE_EVERY': '0', 'SAVAGEWIND_VR_STEREO': '1',
           'SAVAGEWIND_VR_ROOMSCALE': '0'}
    env.update(MODES[a.mode])
    if a.view == 'third':
        env['SAVAGEWIND_VR_VIEW'] = 'third'
    game, proc, log = re_run.boot(a.save, out, env, ['0 head 0 1.7 0 0 0 0'])
    seq = [0]

    def send(*lines):
        seq[0] += 1
        with open(live, 'w') as f:
            f.write('seq {}\n{}\n'.format(seq[0], '\n'.join(lines)))
        until = time.monotonic() + 5
        while time.monotonic() < until:
            try:
                with open(live + '.ack') as f:
                    if int(f.read().split()[0]) >= seq[0]:
                        return
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.03)

    def wait_shot(tag, n, limit=300):
        """until the run of captures is written (a capture stalls the game: seconds a frame)"""
        t0 = time.monotonic()
        want = 'capture %s_%d_' % (tag, n - 1)
        while time.monotonic() - t0 < limit:
            if want in T.fake_log(out):
                return True
            time.sleep(0.5)
        return False

    def frame_now():
        try:
            return int(open(live + '.ack').read().split()[1])
        except (OSError, ValueError, IndexError):
            return 0

    def wait_frames(k, limit=120):
        f0 = frame_now()
        t0 = time.monotonic()
        while time.monotonic() - t0 < limit:
            send('stick {} 0.6 0'.format(R))
            if frame_now() >= f0 + k:
                return
            time.sleep(0.3)

    tags = []
    closes = []
    closes_bad = []
    try:
        send('stick {} 0.6 0'.format(R))
        time.sleep(1.5)
        send('stick {} 0.6 0'.format(R), 'shot pre 8')
        tags.append(('pre', 8))
        wait_shot('pre', 8)
        for r in range(a.rounds):
            send('stick {} 0 0'.format(R))
            time.sleep(0.5)
            game.cmd('press', a.menu, ok=False)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 10 and T.vr_state(game).get('world_view') is not False:
                time.sleep(0.1)
            paused = T.vr_state(game).get('world_view') is False
            time.sleep(2)   # (the menu settles)
            send('stick {} 0 0'.format(R))
            closes.append(frame_now())
            game.cmd('press', a.menu, ok=False)
            # (captured from the press on: the frames still on the menu are the virtual screen's, no eye views, left
            # out; the first ones back in the world are the ones that flickered)
            send('stick {} 0.6 0'.format(R), 'shot post{} {}'.format(r, a.post))
            got = wait_shot('post%d' % r, a.post)
            print('round {}: menu {} {}, {} post frames captured'.format(
                r, a.menu, 'open' if paused else 'NOT seen open', a.post if got else 'not all'))
            tags.append(('post%d' % r, a.post))
            wait_frames(180)   # (~2 s of game at 90 Hz)
            send('stick {} 0.6 0'.format(R), 'shot late{} 8'.format(r))
            tags.append(('late%d' % r, 8))
            wait_shot('late%d' % r, 8)
        send('stick {} 0 0'.format(R))
        st = T.vr_state(game)
        time.sleep(1)
    finally:
        perf_routes.stop_game(game, proc, log)
    gl = open(os.path.join(out, 'game.log'), encoding='utf-8', errors='replace').read()
    m = re.search(r'^\[vr\] rendering: (.*)$', gl, re.M)
    print('rendering:', m.group(1) if m else '?')
    print('present queue orphans logged:', len(re.findall(r'present queue: a right eye without', gl)))
    fl = T.fake_log(out)
    seqf = [(int(f), t) for f, t in re.findall(r'^frame (\d+) display_time \S+ layers \d+ (\S+)', fl, re.M)]
    for c0 in closes:   # (what the headset got from the menu's close on: world = the eyes, screen = the virtual screen)
        runs = []
        for f, t in seqf:
            if f < c0 or f > c0 + 200:
                continue
            k = 'world' if t.startswith('projection') else 'screen'
            if runs and runs[-1][0] == k:
                runs[-1][1] += 1
            else:
                runs.append([k, 1])
        print('from frame {}: '.format(c0) + ' '.join('{}x{}'.format(k, n) for k, n in runs))
        if sum(1 for k, n in runs if k == 'screen') > 1:
            print('  FAIL the view went back to the virtual screen after the menu closed')
            closes_bad.append(c0)
    fov = dict((t, [float(x) for x in f]) for t, *f in re.findall(r'capture (\S+) fov (\S+) (\S+) (\S+) (\S+)', fl))
    cap = os.path.join(out, 'cap')
    rows = {}
    for tag, n in tags:
        res = []
        for i in range(n):
            lt = next((t for t in sorted(fov) if re.fullmatch(r'%s_%d(_layer\d+)?_view0' % (tag, i), t)), None)
            if not lt:
                res.append(None)
                continue
            rt = lt[:-1] + '1'
            res.append(compare(grid(os.path.join(cap, lt + '.ppm'), fov[lt]),
                               grid(os.path.join(cap, rt + '.ppm'), fov[rt])))
        rows[tag] = res
    pre = [r for r in rows.get('pre', []) if r]
    base = max([r[1] for r in pre] + [0.5])
    lim = max(3 * base, 2.0)
    ok = True
    bad_total = 0
    for tag, res in rows.items():
        got = [r for r in res if r]
        bad = [i for i, r in enumerate(res) if r and (r[0] != 0 or r[1] > lim)]
        miss = sum(1 for r in res if r is None)
        bad_total += len(bad) if tag != 'pre' else 0
        print('{:7} {:2} frames, {} not captured; eyes apart in {}: {}'.format(
            tag, len(res), miss, len(bad), ' '.join(
                '{}:dx{}/{:.1f}%'.format(i, res[i][0], res[i][1]) for i in bad[:12])))
        if got:
            print('        dx {}  differing% max {:.2f} median {:.2f}'.format(
                sorted(set(r[0] for r in got)), max(r[1] for r in got), float(np.median([r[1] for r in got]))))
        if tag != 'pre' and miss > len(res) // 2:
            ok = False
    print('limit: dx 0 and differing part <= {:.2f}% (3x the frames before the menu)'.format(lim))
    print('vr state at the end: world_view {} stereo_pairs {}'.format(st.get('world_view'), st.get('stereo_pairs')))
    ok &= bad_total == 0 and bool(pre) and not closes_bad
    print('PASS' if ok else 'FAIL ({} frames after a menu with the eyes apart)'.format(bad_total))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
