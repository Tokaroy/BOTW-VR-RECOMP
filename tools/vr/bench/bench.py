#!/usr/bin/env python3
"""VR frame rate against fake_xr (docs/vr/PERFORMANCE.md): per run, ~12 s in the world at the Great Plateau, then
--measure seconds: the headset's frames a second (the `vr` command's frames), the presents a second (`state`'s frame:
two a headset frame in both stereo modes, one in mono - not the game's updates), the world camera's updates a headset
frame (the `vr` command's camera_updates against its frames: the game sets ~3 a game frame, so ~6 in normal stereo and
~3 with multiview or mono - compare them, the ratio is the game's updates a pair), the last 10 s of
the pose's lead (`vr lead`: how long after the time the views and hands were located for the picture is shown -
how far the hands trail moving controllers), the headset's frame times (`vr frametimes 10`: a pair of eyes each, comparable between the modes) and of the presents'
(`frames 10`), the GPUs' use (nvidia-smi, when there is one) and the freezes over 100 ms in the log; the mode, CPU and
driver the run had. Each run's result.json in <out>/<case>/<run>/; the median of the runs printed last (SUMMARY).

  python tools/vr/bench/bench.py --case base --exe build/savagewind.exe --save <scratch save> [--env K=V ...]
  python tools/vr/bench/bench.py --ab 5 --exe-a A/savagewind.exe --exe-b B/savagewind.exe ...   (interleaved A/B)
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def cpu_name():
    try:
        if sys.platform == 'win32':
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            return winreg.QueryValueEx(k, 'ProcessorNameString')[0].strip()
        for line in open('/proc/cpuinfo'):
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return '?'


def run_info(log_text):
    """the stereo mode and the driver, as the game's log says them"""
    mode = 'stereo (a frame per eye)'
    if '[vr] mono: one picture' in log_text:
        mode = 'mono'
    elif '[vk-mv] multiview: both eyes' in log_text:
        mode = 'multiview'
    elif '[vr] synchronous stereo' in log_text:
        mode = 'synchronous stereo (replay)'
    drv = next((ln.split('driver:', 1)[1].strip() for ln in log_text.splitlines() if ln.startswith('[vk] driver:')), '?')
    return {'mode': mode, 'driver': drv, 'cpu': cpu_name()}


def gpu_sampler(stop, out):
    while not stop.is_set():
        try:
            r = subprocess.run(['nvidia-smi', '--query-gpu=index,utilization.gpu', '--format=csv,noheader,nounits'],
                               capture_output=True, text=True, timeout=5)
            for line in r.stdout.strip().splitlines():
                i, u = [x.strip() for x in line.split(',')]
                out.setdefault(i, []).append(float(u))
        except Exception:
            return   # (no nvidia-smi: no GPU numbers)
        stop.wait(0.5)


def one_run(a, run_dir):
    game, proc, log = common.launch(a, run_dir)
    res = {}
    try:
        common.ready(game, proc, a.boot)
        stop, gpu = threading.Event(), {}
        th = threading.Thread(target=gpu_sampler, args=(stop, gpu), daemon=True)
        game.cmd('vr', 'lead', ok=False, timeout=30)   # (resets the pose lead)
        v0 = game.cmd('vr', ok=False, timeout=60); s0 = game.cmd('state'); t0 = time.monotonic()
        th.start()
        time.sleep(a.measure)
        v1 = game.cmd('vr', ok=False, timeout=60); s1 = game.cmd('state'); t1 = time.monotonic()
        stop.set(); th.join()
        fr = game.cmd('frames', 10, ok=False, timeout=30)
        pf = game.cmd('vr', 'frametimes', 10, ok=False, timeout=30)
        ld = game.cmd('vr', 'lead', ok=False, timeout=30)
        dt = t1 - t0
        hmd = v1['frames'] - v0['frames']
        res = {'hmd_fps': hmd / dt, 'game_fps': (s1['frame'] - s0['frame']) / dt,
               'updates_per_pair': (v1.get('camera_updates', 0) - v0.get('camera_updates', 0)) / max(hmd, 1),
               'pairs10': pf if isinstance(pf, dict) and 'count' in pf else {},
               'pose_lead_ms': ld.get('pose_lead_ms', 0) if isinstance(ld, dict) else 0,
               'pose_lead_max_ms': ld.get('pose_lead_max_ms', 0) if isinstance(ld, dict) else 0,
               'frames10': fr, 'gpu': {k: statistics.mean(v) for k, v in gpu.items() if v}}
    finally:
        common.stop(game, proc, log)
    res['freezes'] = common.freezes(run_dir)
    text = open(os.path.join(run_dir, 'game.log'), encoding='utf-8', errors='replace').read()
    res['second_queue'] = 'second queue)' in text
    res.update(run_info(text))
    return res


def summary(case, results):
    ok = [r for r in results if 'hmd_fps' in r]
    if not ok:
        return {'case': case, 'n': 0}
    return {'case': case, 'n': len(ok), 'hmd_fps': statistics.median(r['hmd_fps'] for r in ok),
            'game_fps': statistics.median(r['game_fps'] for r in ok),
            'p95_ms': statistics.median(r['frames10'].get('frame_ms_p95', 0) for r in ok),
            'pair_p95_ms': statistics.median(r.get('pairs10', {}).get('frame_ms_p95', 0) for r in ok),
            'pair_p99_ms': statistics.median(r.get('pairs10', {}).get('frame_ms_p99', 0) for r in ok),
            'updates_per_pair': statistics.median(r.get('updates_per_pair', 0) for r in ok),
            'pose_lead_ms': statistics.median(r.get('pose_lead_ms', 0) for r in ok),
            'mode': sorted({r.get('mode', '?') for r in ok}), 'cpu': ok[0].get('cpu', '?'),
            'driver': ok[0].get('driver', '?'),
            'gpu_max': statistics.median(max(r['gpu'].values()) if r['gpu'] else 0 for r in ok),
            'freezes': [len(r['freezes']) for r in ok], 'runs_hmd': [round(r['hmd_fps'], 1) for r in ok]}


def run_case(a, case, exe, runs):
    a.exe = exe
    out = []
    for i in range(runs):
        run_dir = os.path.join(a.out, case, str(i))
        shutil.rmtree(run_dir, ignore_errors=True)
        r = one_run(a, run_dir)
        json.dump(r, open(os.path.join(run_dir, 'result.json'), 'w'), indent=1)
        print(case, i, json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()
                                   if k in ('hmd_fps', 'game_fps', 'updates_per_pair', 'mode', 'gpu', 'freezes')}), flush=True)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common.add_args(ap)
    ap.set_defaults(exe=None)
    for act in ap._actions:
        if act.dest == 'exe':
            act.required = False
    ap.add_argument('--case', default='run')
    ap.add_argument('--runs', type=int, default=3)
    ap.add_argument('--boot', type=float, default=300)
    ap.add_argument('--measure', type=float, default=15)
    ap.add_argument('--ab', type=int, default=0, help='interleaved A/B: this many rounds of A then B')
    ap.add_argument('--exe-a')
    ap.add_argument('--exe-b')
    ap.add_argument('--env-b', nargs='*', default=[], help='KEY=VALUE for B only (B may be the same exe)')
    a = ap.parse_args()
    if a.ab:
        base_env = list(a.env)
        res = {'A': [], 'B': []}
        for r in range(a.ab):
            for k, exe in (('A', a.exe_a), ('B', a.exe_b or a.exe_a)):
                a.env = base_env + (a.env_b if k == 'B' else [])
                res[k] += run_case(a, '%s_%s_%d' % (a.case, k, r), exe, 1)
        for k in ('A', 'B'):
            print('SUMMARY', json.dumps(summary('%s_%s' % (a.case, k), res[k])))
        return
    if not a.exe:
        raise SystemExit('--exe (or --ab with --exe-a / --exe-b)')
    print('SUMMARY', json.dumps(summary(a.case, run_case(a, a.case, a.exe, a.runs))))


if __name__ == '__main__':
    main()
