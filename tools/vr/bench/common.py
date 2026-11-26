"""Shared launch code of the VR benchmarks (tools/vr/bench): the game in VR against fake_xr, on a copy of a save, with
its own settings file, driven over the control port. docs/vr/PERFORMANCE.md says how they are used.

Every script takes:
  --exe   a VR=1 build's savagewind.exe (variants each in a folder of their own, named savagewind.exe: the game
          library imports the executable by that name)
  --data  the folder the game runs in (with `extracted/`, your own game files; build/vr/fake_xr.json is looked for here
          first, then in this checkout)
  --save  a save folder to copy for each run (never your own: a scratch copy)
  --out   where each run's folder goes (its log, captures, results)
"""
import os
import re
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import perf_routes  # noqa: E402

FREEZE = re.compile(r'(acquire blocked|present took|a wait for a submission took)\D*(\d+)\s*ms')


def add_args(ap, port=7900):
    ap.add_argument('--exe', required=True)
    ap.add_argument('--data', default=REPO, help="the game's working folder (with extracted/)")
    ap.add_argument('--save', required=True, help='a save folder, copied for each run')
    ap.add_argument('--out', default=os.path.join(REPO, 'build', 'bench'))
    ap.add_argument('--env', nargs='*', default=[], help='extra KEY=VALUE for the game')
    ap.add_argument('--ini', nargs='*', default=[], help="settings lines 'key = value' over the defaults (antialias = off ...)")
    ap.add_argument('--port', type=int, default=port)
    ap.add_argument('--visible', action='store_true', help='show the game window (hidden by default)')


def fake_xr_json(a):
    for root in (a.data, REPO):
        p = os.path.join(root, 'build', 'vr', 'fake_xr.json')
        if os.path.exists(p):
            return p
    raise SystemExit('no build/vr/fake_xr.json: make VR=1 build/vr/fake_xr.dll (Linux: .so)')


def launch(a, run_dir, place='plateau', script_lines=None, live=None, hz='500', extra_env=None, ini=None):
    """Start the game for one run in run_dir: (game, proc, log). The headset is fake_xr at `hz` (500: as fast as the
    game goes, the headset never the limit), 1800 pixels high per eye, stereo, the window hidden, TAA. ini: settings
    lines that replace these (e.g. ['antialias = off', 'vr_render_mode = 2', 'vr_experimental = 1']); a.ini too."""
    os.makedirs(os.path.join(run_dir, 'cap'), exist_ok=True)
    save = os.path.join(run_dir, 'save')
    if not os.path.isdir(save):
        shutil.copytree(a.save, save)
    lines = {'window_size': '1280x720', 'frame_rate': '0', 'vsync': 'off', 'perf_overlay': 'off', 'frame_generation': '0',
             'fullscreen': '0', 'antialias': 'taa'}
    for kv in list(ini or []) + list(getattr(a, 'ini', None) or []):
        k, v = kv.split('=', 1)
        lines[k.strip()] = v.strip()
    ini = os.path.join(run_dir, 'settings.ini')
    with open(ini, 'w') as f:
        f.write(''.join('%s = %s\n' % kv for kv in lines.items()))
    script = os.path.join(run_dir, 'fake_xr_script.txt')
    with open(script, 'w') as f:
        f.write('\n'.join(script_lines or ['# a still head']) + '\n')
    env = dict(os.environ,
               SAVAGEWIND_VR='1', XR_RUNTIME_JSON=fake_xr_json(a),
               FAKE_XR_LOG=os.path.join(run_dir, 'fake_xr.log'), FAKE_XR_CAPTURE=os.path.join(run_dir, 'cap'),
               FAKE_XR_CAPTURE_EVERY='0', FAKE_XR_SCRIPT=script, FAKE_XR_HZ=hz,
               SAVAGEWIND_VR_STEREO='1', SAVAGEWIND_VR_HEIGHT='1800',
               SAVAGEWIND_NO_LAUNCHER='1', SAVAGEWIND_HIDDEN='1', SAVAGEWIND_SAVE_DIR=save,
               SAVAGEWIND_SETTINGS=ini, SAVAGEWIND_CONTROL=str(a.port), SAVAGEWIND_SCRIPT_CLOCK='1',
               SAVAGEWIND_INPUT=perf_routes.CONTINUE, SAVAGEWIND_TEST_WARP=place,
               SAVAGEWIND_TEST_WEATHER='0')
    if live:
        env['FAKE_XR_LIVE'] = live
    if a.visible:
        env.pop('SAVAGEWIND_HIDDEN')
    for kv in list(a.env) + list(extra_env or []):
        k, v = kv.split('=', 1)
        env[k] = v
    if os.name == 'nt' and os.path.isdir(r'C:\msys64\ucrt64\bin'):   # (the MSYS2 runtime DLLs of a dev build)
        env['PATH'] = r'C:\msys64\ucrt64\bin' + os.pathsep + env.get('PATH', '')
    log = open(os.path.join(run_dir, 'game.log'), 'wb')
    proc = subprocess.Popen([a.exe, 'extracted'], cwd=a.data, env=env, stdout=log, stderr=subprocess.STDOUT)
    return perf_routes.Game(a.port), proc, log


def ready(game, proc, boot=300, settle=10.5):
    """In the world, settled (~12 s with the two B presses that close the loading's leftovers)."""
    perf_routes.wait_world(game, proc, boot)
    time.sleep(settle)
    for _ in range(2):
        game.cmd('press', 'b', ok=False)
        time.sleep(0.7)


def stop(game, proc, log):
    perf_routes.stop_game(game, proc, log)


def freezes(run_dir, over_ms=100):
    text = open(os.path.join(run_dir, 'game.log'), encoding='utf-8', errors='replace').read()
    return [m.group(0) for m in FREEZE.finditer(text) if int(m.group(2)) > over_ms]
