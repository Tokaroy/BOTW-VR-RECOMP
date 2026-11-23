#!/usr/bin/env python3
"""A window the system keeps at another size than the headset's eyes (Steam Frame standalone, gamescope), against
fake_xr: the game is started with SAVAGEWIND_WINDOW=1280x720 (a test window keeps its size), so the window is 16:9 and
smaller than the eyes (1374x1440 at the default 1440 lines). Passes when the game still draws at the eyes' size, the
eyes' swapchains are that size, and the stereo pair still fuses (test_vr_game.py's stereo scenario: the right eye's
shift the same as with a headset-shaped window). Run with the HUD apart and on the picture.

  python tools/vr/test_vr_fixed_window.py --save <scratch save> [--out build/vr/fixed_window]
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/fixed_window')
    a = ap.parse_args()
    ok = True
    for hud in ('1', '0'):
        out = os.path.abspath(os.path.join(a.out, 'hud' + hud))
        env = dict(os.environ, SAVAGEWIND_WINDOW='1280x720', SAVAGEWIND_VR_HUD=hud, PYTHONUNBUFFERED='1')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'test_vr_game.py'), '--save', a.save, '--out', out,
                            '--scenario', 'stereo'], env=env, capture_output=True, text=True)
        text = r.stdout + r.stderr
        glog = open(os.path.join(out, 'stereo', 'game.log'), errors='replace').read()
        xlog = open(os.path.join(out, 'stereo', 'fake_xr.log'), errors='replace').read()
        eyes = re.search(r'\[vr\] headset eye images \d+x\d+: window (\d+)x(\d+)', glog)
        want = '%sx%s' % eyes.groups() if eyes else None
        dx = re.search(r'best shift dx (-?\d+) dy (-?\d+)', text)

        def check(c, what):
            nonlocal ok
            print(('  ok   ' if c else '  FAIL ') + 'HUD %s: ' % ('apart' if hud == '1' else 'on the picture') + what)
            ok &= bool(c)

        check(want and '[vr] game image %s in a 1280x720 window' % want in glog,
              'the game draws at the eyes\' size (%s) in a 1280x720 window' % want)
        check(want and re.search(r'swapchain %s x1 format' % want, xlog), 'the eyes\' swapchains are %s' % want)
        check(dx and int(dx.group(1)) < 0 and -5 <= int(dx.group(1)) and int(dx.group(2)) == 0,
              'the eyes fuse: right eye shifted left by -3 +-2 samples, none up or down (%s)' % (dx.groups(),) if dx else 'the eyes fuse: no stereo shift measured')
        check('the eyes see different pictures' in text and 'FAIL the right eye' not in text, 'stereo scenario\'s eye checks')
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
