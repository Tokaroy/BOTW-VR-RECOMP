#!/usr/bin/env python3
"""Savage Wind Configuration kept open while playing (ui/launcher.mm live_*, control_settings.c control_settings_live),
against fake_xr: the start screen's PLAY (SAVAGEWIND_LAUNCHER_AUTOPLAY) hands the headset over, the configuration
restarts as the same process with VR off and starts the game in a process of its own; the game gets the headset, and a
change to savagewind.ini (what the configuration writes) applies to it live. Closing the game leaves the configuration
open. It opens windows on the desktop.

  python tools/vr/test_vr_live_launcher.py --save <scratch save> [--exe build/savagewind] [--out build/vr/live_launcher]
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_vr_game as T  # noqa: E402
import perf_routes  # noqa: E402


def children(pid):
    try:
        with open('/proc/{}/task/{}/children'.format(pid, pid)) as f:
            return [int(x) for x in f.read().split()]
    except OSError:
        return []


def cmdline(pid):
    try:
        with open('/proc/{}/cmdline'.format(pid), 'rb') as f:
            return f.read().split(b'\0')
    except OSError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', required=True)
    ap.add_argument('--exe', default=T.EXE)
    ap.add_argument('--out', default='build/vr/live_launcher')
    ap.add_argument('--port', type=int, default=7795)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    shutil.copytree(a.save, os.path.join(out, 'save'))
    ini = os.path.join(out, 'settings.ini')
    with open(ini, 'w') as f:
        f.write('window_size = 1280x720\nframe_rate = 0\nvsync = off\nfullscreen = 0\nlauncher_stays_open = 1\n'
                'menu_tip_seen = 1\n')
    env = dict(os.environ, SAVAGEWIND_VR='1', XR_RUNTIME_JSON=os.path.join(T.TREE, 'build', 'vr', 'fake_xr.json'),
               FAKE_XR_LOG=os.path.join(out, 'fake_xr.log'), FAKE_XR_CAPTURE_EVERY='0',
               SAVAGEWIND_SAVE_DIR=os.path.join(out, 'save'), SAVAGEWIND_SETTINGS=ini,
               SAVAGEWIND_CONTROL=str(a.port), SAVAGEWIND_SCRIPT_CLOCK='1', SAVAGEWIND_INPUT=perf_routes.CONTINUE,
               SAVAGEWIND_TEST_WARP='plateau', SAVAGEWIND_LAUNCHER_AUTOPLAY='once', SAVAGEWIND_LIVE_TEST='1',
               SAVAGEWIND_LIVE_GAME_LOG=os.path.join(out, 'game.log'))
    for k in ('SAVAGEWIND_NO_LAUNCHER', 'SAVAGEWIND_HIDDEN'):
        env.pop(k, None)
    log = open(os.path.join(out, 'launcher.log'), 'wb')
    proc = subprocess.Popen([os.path.abspath(a.exe), '--config', 'extracted'], cwd=T.TREE, env=env, stdout=log,
                            stderr=subprocess.STDOUT)
    ok = True

    def check(c, what):
        nonlocal ok
        print(('  ok   ' if c else '  FAIL ') + what)
        ok &= bool(c)

    game = perf_routes.Game(a.port)
    try:
        # (the start screen answers first, and its connection goes with its restart: connect again)
        end = time.monotonic() + 240
        while True:
            try:
                perf_routes.wait_world(game, proc, max(end - time.monotonic(), 1))
                break
            except ValueError:
                game.close()
                game = perf_routes.Game(a.port)
        time.sleep(6)
        kids = [k for k in children(proc.pid) if b'--play' in cmdline(k)]
        check(proc.poll() is None and b'--config' in cmdline(proc.pid),
              'the configuration is still open (pid {}, restarted as --config)'.format(proc.pid))
        check(len(kids) == 1, 'the game runs in a process of its own ({})'.format(kids))
        v1 = T.vr_state(game)
        time.sleep(2)
        v2 = T.vr_state(game)
        frames = v2.get('world_frames', 0) - v1.get('world_frames', 0)
        check(frames > 20, 'the game has the headset: {} world frames in 2 s'.format(frames))
        with open(ini, 'a') as f:
            f.write('vr_ipd_scale = 85\nvr_eye_resolution = 1080\n')
        time.sleep(3)
        g = game.cmd('get', ok=False)
        check(g.get('vr_ipd_scale') == 85 and g.get('vr_eye_resolution') == 1080,
              'savagewind.ini changed beside it applies live (eye separation {}, eye resolution {})'
              .format(g.get('vr_ipd_scale'), g.get('vr_eye_resolution')))
        game.cmd('exit', ok=False)
        for _ in range(60):
            if not [k for k in kids if os.path.exists('/proc/{}'.format(k)) and b'--play' in cmdline(k)]:
                break
            time.sleep(0.5)
        time.sleep(2)
        check(proc.poll() is None, 'closing the game leaves the configuration open')
    finally:
        for k in children(proc.pid):
            os.kill(k, signal.SIGKILL)
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        log.close()
    glog = open(os.path.join(out, 'game.log'), errors='replace').read() if os.path.exists(os.path.join(out, 'game.log')) else ''
    llog = open(os.path.join(out, 'launcher.log'), errors='replace').read()
    check('[launcher] started the game in a process of its own' in llog, 'launcher.log says the game was started')
    check('applied live' in glog, "the game's log says the change was applied live")
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
