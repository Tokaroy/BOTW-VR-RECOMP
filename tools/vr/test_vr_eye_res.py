#!/usr/bin/env python3
"""Options > VR > Eye resolution applied live (V08, docs/vr/FEATURES.md), against fake_xr: in play the setting goes
1440 (the default) -> 1080 -> 2160 -> back to 1440 through the `set` command (as the Options page stores it); each
time the game draws at the new eye size ([vr] game image / eye resolution lines in the log), fake_xr gets eye
swapchains of that size, and the eyes keep getting pictures (world frames go on).

  python tools/vr/test_vr_eye_res.py --save <scratch save> [--out build/vr/eye_res]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/eye_res')
    ap.add_argument('--exe', default=T.EXE)
    a = ap.parse_args()
    T.EXE = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    game, proc, log = re_run.boot(a.save, out, {'FAKE_XR_CAPTURE_EVERY': '0'})
    frames = []
    try:
        for h in ('1080', '2160', '0'):
            print('set', h, game.cmd('set', 'vr_eye_resolution', h, ok=False))
            time.sleep(3)
            v1 = T.vr_state(game).get('world_frames', 0)
            time.sleep(1)
            v2 = T.vr_state(game).get('world_frames', 0)
            frames.append(v2 - v1)
    finally:
        perf_routes.stop_game(game, proc, log)
    glog = open(os.path.join(out, 'game.log'), errors='replace').read()
    xlog = open(os.path.join(out, 'fake_xr.log'), errors='replace').read()
    ok = True

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    m = re.search(r'\[vr\] headset eye images (\d+)x(\d+): window (\d+)x(\d+)', glog)
    aspect = int(m.group(1)) / int(m.group(2)) if m else 1
    for h in (1080, 2160, 1440):
        w = int(h * aspect + 0.5) & ~1
        size = '%dx%d' % (w, h)
        check('[vr] eye resolution: %s' % size in glog or (h == 1440 and m and m.group(4) == '1440'),
              '%d lines: the eye size set to %s' % (h, size))
        check('[vr] game image %s' % size in glog, '%d lines: the game draws %s' % (h, size))
        check(re.search(r'swapchain %s x1 format' % size, xlog) is not None, '%d lines: fake_xr gets %s eye swapchains' % (h, size))
    check(all(f > 20 for f in frames), 'the eyes keep getting pictures after each change (%s world frames a second)' % frames)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
