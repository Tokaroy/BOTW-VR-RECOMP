#!/usr/bin/env python3
"""The sun's lens flares in VR (a player's report on the build of 2026-11-25: flares still seen with them off, and
looking flat), against fake_xr: the head swept round at a pitch (FAKE_XR_LIVE, a capture at each yaw), twice - as VR
has them (flares off whatever Video says: runtime/nvn/vulkan/exec.c vr_no_flare, the sun's occlusion query answered
with 0 samples) and with SAVAGEWIND_VR_LENS_FLARE=1 (the Video option decides, as flat).

What it shows, per yaw: each eye's mean level in both runs and how much of the picture changes between them (a flare
the switch removes is a bright patch only in the second run), and the occlusion queries the game made (the log's
`[oq]` lines, SAVAGEWIND_LOG_OCCLUSION). Judged: the VR run makes no occlusion query with samples (the switch works as
designed). Not judged: whether something flare-like is left in the VR run - look at the side-by-side PNGs
(<out>_<run>/y<yaw>.png); a glare the switch does not reach is the next thing to find (its shaders with
SAVAGEWIND_LOG_NEW_FS). The sun's place depends on the save's time of day: pass --pitch / a save at another hour if no
yaw shows it.

  python tools/vr/test_vr_sun_flare.py --save <scratch save> [--out build/vr/flare] [--pitch 15] [--step 30]
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import perf_routes  # noqa: E402
import test_vr_game as T  # noqa: E402


def run(save, out, env_extra, yaws, pitch):
    live = os.path.join(out, 'fake_xr_live.txt')
    os.makedirs(out, exist_ok=True)
    for p in (live, live + '.ack'):
        if os.path.exists(p):
            os.unlink(p)
    env = {'SAVAGEWIND_VR_STEREO': '1', 'FAKE_XR_LIVE': live, 'FAKE_XR_CAPTURE_EVERY': '0',
           'SAVAGEWIND_LOG_OCCLUSION': '200', 'SAVAGEWIND_VR_ROOMSCALE': '0'}
    env.update(env_extra)
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
                        return
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.03)

    try:
        for y in yaws:
            send('head 0 1.7 0 {} {} 0'.format(y, pitch))
            time.sleep(1.5)   # (TAA and the exposure settle)
            send('head 0 1.7 0 {} {} 0'.format(y, pitch), 'shot y{}'.format(y))
            time.sleep(2.5)   # (a capture stalls the game: keep them apart)
    finally:
        perf_routes.stop_game(game, proc, log)
    gl = open(os.path.join(out, 'game.log'), encoding='utf-8', errors='replace').read()
    oq = [float(s) for s in re.findall(r'^\[oq\] \d+ queries: (\S+) samples', gl, re.M)]
    return oq


def load(out, tag, view):
    import numpy as np
    from PIL import Image
    cap = os.path.join(out, 'cap')
    name = next((f for f in sorted(os.listdir(cap)) if f.startswith(tag + '_') and f.endswith('_view%d.ppm' % view)),
                None) if os.path.isdir(cap) else None
    return None if name is None else np.asarray(Image.open(os.path.join(cap, name)).convert('RGB'), dtype=np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/flare')
    ap.add_argument('--pitch', type=float, default=15)
    ap.add_argument('--step', type=int, default=30)
    a = ap.parse_args()
    yaws = list(range(0, 360, a.step))
    out = os.path.abspath(a.out)
    runs = {'vr': (out + '_vr', {}), 'flat': (out + '_flat', {'SAVAGEWIND_VR_LENS_FLARE': '1'})}
    oq = {k: run(a.save, d, env, yaws, a.pitch) for k, (d, env) in runs.items()}
    print('occlusion queries logged: VR {} (with samples {}), flat option {} (with samples {})'.format(
        len(oq['vr']), sum(1 for s in oq['vr'] if s > 0), len(oq['flat']), sum(1 for s in oq['flat'] if s > 0)))
    from PIL import Image
    import numpy as np
    for y in yaws:
        row = []
        for view in (0, 1):
            v, f = load(runs['vr'][0], 'y%d' % y, view), load(runs['flat'][0], 'y%d' % y, view)
            if v is None or f is None:
                row.append('eye %d: no capture' % view)
                continue
            d = np.abs(v - f).max(axis=2)
            brighter = ((f.sum(axis=2) - v.sum(axis=2)) > 60).mean() * 100
            row.append('eye {}: mean {:.0f} / {:.0f}, changed {:.1f}%, brighter with flares {:.2f}%'.format(
                view, v.mean(), f.mean(), (d > 24).mean() * 100, brighter))
            if view == 0:
                Image.fromarray(np.concatenate([v, f], axis=1).clip(0, 255).astype(np.uint8)).save(
                    os.path.join(out + '_vr', 'y%d.png' % y))
        print('yaw {:3}: {}'.format(y, ' | '.join(row)))
    ok = not any(s > 0 for s in oq['vr'])
    print('the VR run made no occlusion query with samples:', 'ok' if ok else 'FAIL')
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
