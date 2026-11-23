#!/usr/bin/env python3
"""Savage Wind's overlay menu in the headset (docs/VR.md), against fake_xr: in play the headset gets the eyes'
pictures; the keyboard command and a held VR menu button open it on the virtual screen (a quad layer, no projection);
the VR menu button also closes it again. Read from `vr` (world_view, world_frames) and fake_xr's log (each ended
frame's layer kinds).

  python tools/vr/test_vr_overlay.py --save <scratch save> [--out build/vr/overlay]
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


def layer_kinds(path, start):
    with open(path, errors='replace') as f:
        f.seek(start)
        return re.findall(r'frame \d+ display_time \S+ layers \d+ (.*)', f.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/overlay')
    ap.add_argument('--exe', default=T.EXE)
    a = ap.parse_args()
    T.EXE = os.path.abspath(a.exe)
    out = os.path.abspath(a.out)
    live = os.path.join(out, 'fake_xr_live.txt')
    for path in (live, live + '.ack'):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    game, proc, log = re_run.boot(a.save, out, {'FAKE_XR_LIVE': live}, ['0 head 0 1.7 0 0 0 0'])
    fl = os.path.join(out, 'fake_xr.log')
    ok = True

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    def live_button(seq, down):
        with open(live, 'w') as f:
            f.write('seq {}\nbutton /user/hand/left/input/menu/click {}\n'.format(seq, int(down)))
        ack = live + '.ack'
        until = time.monotonic() + 3
        while time.monotonic() < until:
            try:
                with open(ack) as f:
                    if f.read().startswith(str(seq) + ' '):
                        return True
            except OSError:
                pass
            time.sleep(0.03)
        return False

    ack1 = ack2 = ack3 = False
    vh = vr = vclosed = {}
    try:
        v0 = T.vr_state(game)
        m0 = os.path.getsize(fl)
        time.sleep(2)
        v1 = T.vr_state(game)
        play = layer_kinds(fl, m0)
        print(game.cmd('menu', 'open', ok=False))
        time.sleep(1)
        m1 = os.path.getsize(fl)
        vm = T.vr_state(game)
        time.sleep(2)
        vm2 = T.vr_state(game)
        menu = layer_kinds(fl, m1)
        print(game.cmd('menu', 'close', ok=False))
        time.sleep(1)
        vc = T.vr_state(game)

        # The Touch menu action is held long enough to open the overlay, released, then held again to close it.
        ack1 = live_button(1, True)
        time.sleep(1)
        vh = T.vr_state(game)
        ack2 = live_button(2, False)
        time.sleep(0.5)
        vr = T.vr_state(game)
        ack3 = live_button(3, True)
        time.sleep(1)
        vclosed = T.vr_state(game)
        live_button(4, False)
    finally:
        perf_routes.stop_game(game, proc, log)
    proj = lambda ks: sum('projection' in k for k in ks)  # noqa: E731
    quad = lambda ks: sum('projection' not in k and 'quad' in k for k in ks)  # noqa: E731
    print('    in play: {} frames ({} with the eyes); menu open: {} frames ({} with the eyes, {} the screen alone)'.format(
        len(play), proj(play), len(menu), proj(menu), quad(menu)))
    check(v0.get('world_view') and proj(play) > 50, 'in play the eyes\' pictures')
    check(vm.get('world_view') is False and vm2.get('world_frames') == vm.get('world_frames'),
          'menu open: no eyes\' pictures ({} -> {} world frames)'.format(vm.get('world_frames'), vm2.get('world_frames')))
    check(quad(menu) > 50 and proj(menu) < 5, 'menu open: the virtual screen ({} frames)'.format(quad(menu)))
    check(vc.get('world_view') is True, 'closed: the eyes again')
    check(ack1 and ack2 and ack3 and vh.get('world_view') is False,
          'holding the VR menu button opens the overlay without keyboard input')
    check(vr.get('world_view') is False, 'releasing the button leaves the overlay open')
    check(vclosed.get('world_view') is True, 'holding the VR menu button again closes the overlay')
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
