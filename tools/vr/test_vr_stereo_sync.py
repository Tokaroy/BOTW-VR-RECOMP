#!/usr/bin/env python3
"""Stereo: both eyes of a pair drawn from one place while the view turns (vr_camera.c, the pair's anchor), against
fake_xr. The eyes are drawn in two game frames half a step apart; the right one used to take its own frame's anchor,
so with the turn stick held its picture was turned against the left one's (one eye "desynchronised", 2026-11-24).

With the eyes 0 m apart (FAKE_XR_IPD=0) both pictures, placed by the fields they were submitted with, must be the same
picture: still, and with the right stick held (a smooth turn). --compare runs the same with SAVAGEWIND_VR_PAIR_ANCHOR=0
too (each eye its own anchor), where the turn shows as a sideways shift between the eyes.

  python tools/vr/test_vr_stereo_sync.py --save <scratch save> [--exe build/savagewind] [--out build/vr/stereo_sync]
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import test_vr_game as T  # noqa: E402
import perf_routes  # noqa: E402

R = '/user/hand/right/input/thumbstick'


def run(save, out, extra_env):
    live = os.path.join(out, 'fake_xr_live.txt')
    for path in (live, live + '.ack'):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    env = {'FAKE_XR_LIVE': live, 'FAKE_XR_IPD': '0', 'FAKE_XR_CAPTURE_EVERY': '0', 'SAVAGEWIND_VR_STEREO': '1'}
    env.update(extra_env)
    game, proc, log = re_run.boot(save, out, env, ['0 head 0 1.7 0 0 0 0'])
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
                        return True
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.03)
        return False

    shots = []
    try:
        v0 = T.vr_state(game)
        send('stick {} 0 0'.format(R), 'shot still')
        time.sleep(2)
        shots.append('still')
        send('stick {} 1 0'.format(R))   # (a smooth turn, held)
        time.sleep(1.5)
        for k in range(3):
            send('stick {} 1 0'.format(R), 'shot turn{}'.format(k))
            time.sleep(1.5)
            shots.append('turn{}'.format(k))
        v1 = T.vr_state(game)
        send('stick {} 0 0'.format(R))
        time.sleep(1)
    finally:
        perf_routes.stop_game(game, proc, log)
    fov = dict((t, [float(x) for x in f])
               for t, *f in re.findall(r'capture (\S+) fov (\S+) (\S+) (\S+) (\S+)', T.fake_log(out)))
    res = {}
    for s in shots:
        lt = next((t for t in sorted(fov) if re.fullmatch(re.escape(s) + r'_layer\d+_view0', t)), s + '_view0')
        rt = lt[:-1] + '1'
        lp, rp = os.path.join(out, 'cap', lt + '.ppm'), os.path.join(out, 'cap', rt + '.ppm')
        if not (os.path.exists(lp) and os.path.exists(rp) and lt in fov and rt in fov):
            res[s] = None
            continue
        a, b = T.read_ppm_angles(lp, fov[lt]), T.read_ppm_angles(rp, fov[rt])
        res[s] = T.best_shift(a, b)
    return res, v0, v1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--exe', default=T.EXE)
    ap.add_argument('--out', default='build/vr/stereo_sync')
    ap.add_argument('--compare', action='store_true', help='also run with SAVAGEWIND_VR_PAIR_ANCHOR=0')
    a = ap.parse_args()
    T.EXE = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    ok = True

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    def show(res):
        for s, r in res.items():
            print('    {:6} {}'.format(s, 'no capture' if r is None else
                                     'right against left: dx {} dy {} (0.005-tangent samples), difference {:.1f} '
                                     'there, {:.1f} unshifted'.format(*r)))

    print('== the pair anchor (default)')
    res, v0, v1 = run(a.save, os.path.join(out, 'pair'), {})
    show(res)
    turned = v1.get('pair_anchors', 0) - v0.get('pair_anchors', 0)
    pairs = v1.get('stereo_pairs', 0) - v0.get('stereo_pairs', 0)
    check(pairs > 50 and turned >= pairs * 0.9,
          'right frames drawn with their left frame\'s anchor: {} of {} pairs'.format(turned, pairs))
    for s, r in res.items():
        check(r is not None, '{}: both eyes captured'.format(s))
        if r:
            check(r[0] == 0 and r[1] == 0, '{}: eyes 0 m apart see one picture (shift {} {})'.format(s, r[0], r[1]))
    if a.compare:
        print('== each eye its own anchor (SAVAGEWIND_VR_PAIR_ANCHOR=0, for comparison)')
        res0, _, _ = run(a.save, os.path.join(out, 'own'), {'SAVAGEWIND_VR_PAIR_ANCHOR': '0'})
        show(res0)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
