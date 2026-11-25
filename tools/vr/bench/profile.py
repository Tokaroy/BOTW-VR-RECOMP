#!/usr/bin/env python3
"""Where a thread's time goes in VR (docs/vr/PERFORMANCE.md): the game against fake_xr, ~12 s in the world, then the
runtime's sampling profiler (`prof start` / `prof stop`, tools/swprof.py's format) for --secs seconds; the capture's
samples of --thread (default nvn-queue, the translating thread) by runtime function, time in the driver and the system
given to the runtime function that called it ("sys<-name"), and by source line (addr2line, when there is one).

  python tools/vr/bench/profile.py --case base --exe build/savagewind.exe --save <scratch save> [--env K=V ...]
  python tools/vr/bench/profile.py --only <file.swprof> --exe build/savagewind.exe [--thread nvn-queue]
"""
import argparse
import bisect
import collections
import glob
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def hot(cap_path, exe, thread, top=45):
    import common
    sys.path.insert(0, os.path.join(common.REPO, 'tools'))
    import swprof
    cap = swprof.Capture(cap_path)
    mods = sorted(cap.modules)
    rt = [m for m in mods if m[3] == swprof.MOD_RUNTIME][0]
    sym = swprof.Symbols(exe, rt)
    tids = {tid for name, tid in cap.threads if name == thread}
    fn, addrs, cats = collections.Counter(), collections.Counter(), collections.Counter()
    starts = [m[0] for m in mods]

    def runtime_at(p):
        j = bisect.bisect_right(starts, p) - 1
        return j >= 0 and p < mods[j][0] + mods[j][1] and mods[j][3] == swprof.MOD_RUNTIME

    n = 0
    for t, tid, handle, pcs in cap.samples:
        if tid not in tids or not pcs:
            continue
        n += 1
        a = pcs[0]
        if runtime_at(a):
            fn[sym.name(a)] += 1
            addrs[a - sym.delta] += 1
            cats['runtime'] += 1
        else:
            r = [p for p in pcs if runtime_at(p)]
            fn['sys<-' + (sym.name(r[0]) if r else '?')] += 1
            cats['other'] += 1
    print(n, 'samples of', thread, dict(cats))
    for k, v in fn.most_common(top):
        print('%6.2f%%  %s' % (100 * v / max(n, 1), k))
    a2l = shutil.which('addr2line') or (r'C:\msys64\ucrt64\bin\addr2line.exe' if os.path.exists(r'C:\msys64\ucrt64\bin\addr2line.exe') else None)
    if not a2l:
        return
    tops = addrs.most_common(400)
    out = subprocess.run([a2l, '-f', '-C', '-e', exe], input='\n'.join('0x%x' % x for x, _ in tops),
                         capture_output=True, text=True).stdout.splitlines()
    lines = collections.Counter()
    for (x, c), j in zip(tops, range(0, len(out), 2)):
        lines[out[j] + ' ' + out[j + 1].replace('\\', '/').split('/')[-1]] += c
    print('--- by line')
    for k, v in lines.most_common(60):
        print('%6.2f%%  %s' % (100 * v / max(n, 1), k))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only')
    ap.add_argument('--thread', default='nvn-queue')
    ap.add_argument('--case', default='profile')
    ap.add_argument('--secs', type=float, default=5)
    if '--only' in sys.argv:
        ap.add_argument('--exe', required=True)
        a, _ = ap.parse_known_args()
        hot(a.only, a.exe, a.thread)
        return
    import common
    common.add_args(ap, port=8500)
    a = ap.parse_args()
    run_dir = os.path.join(a.out, a.case)
    shutil.rmtree(run_dir, ignore_errors=True)
    before = set(glob.glob(os.path.join(a.data, 'profile', '*.swprof')))
    game, proc, log = common.launch(a, run_dir)
    try:
        common.ready(game, proc)
        game.cmd('prof', 'start', ok=False)
        time.sleep(a.secs)
        game.cmd('prof', 'stop', ok=False, timeout=60)
        time.sleep(5)   # (the file is written after the stop)
    finally:
        common.stop(game, proc, log)
    new = sorted(set(glob.glob(os.path.join(a.data, 'profile', '*.swprof'))) - before)
    if not new:
        raise SystemExit('no capture written (see %s)' % os.path.join(run_dir, 'game.log'))
    print('capture', new[-1])
    hot(new[-1], a.exe, a.thread)


if __name__ == '__main__':
    main()
