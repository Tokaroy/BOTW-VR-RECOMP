#!/usr/bin/env python3
"""Hand simulator: boots the game in VR against fake_xr and moves the head and both hands (position AND rotation)
while it runs, through fake_xr's live file (FAKE_XR_LIVE), taking pictures and reading Link's arms from the log.

  python tools/vr/handsim.py --save <scratch save> [--out build/vr/handsim] [cmd ...]
  python tools/vr/handsim.py --save <scratch save> -i          (interactive: one command a line)

Poses are in the room (LOCAL = the floor under the start; metres, degrees; yaw 90 turns to -X, pitch up, roll
counter-clockwise looking ahead). The OpenXR grip pose: -Z is where the controller points, +Y up out of the hand.

Commands:
  pose <preset> [left|right|both]       a preset (`presets` lists them), both hands by default
  hand <left|right> x y z yaw pitch roll
  handq <left|right> x y z qx qy qz qw
  rel <left|right> x y z yaw pitch roll   relative to the head (its position and yaw)
  head x y z yaw pitch roll
  sweep <left|right> <yaw|pitch|roll> <from> <to> <steps> [prefix]   turn a hand by steps, a picture each
  move <left|right> x y z yaw pitch roll <s>   there smoothly over s seconds (swings, reaches)
  grip|trigger <left|right> <0..1>     tap <grip|trigger> <left|right> [s]   (a short press)
  button <path> <0|1>   stick <left|right> x y   draw (the weapon out: grip over the right shoulder)
  shot <name>       the window's picture (the eye's view in mono) -> <out>/<name>.png
  xshot <name>      what fake_xr was given (each layer) -> <out>/<name>_layer*.png
  focus | unfocus   the session gets / loses input focus (a headset's own menu, the headset taken off)
  arms              the last line of the arms' solve ([vr-arms] / [vr-hands])
  wait <s>          game <control command...>      presets
"""
import argparse
import math
import os
import re
import shlex
import struct
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re_run  # noqa: E402
import perf_routes  # noqa: E402

HEAD = [0.0, 1.7, 0.0, 0.0, 0.0, 0.0]


def quat_euler(yaw, pitch, roll):
    """fake_xr's euler_pose: yaw(+Y) * pitch(+X) * roll(+Z), degrees -> (x, y, z, w)"""
    def axis(ax, deg):
        h = math.radians(deg) / 2
        s = math.sin(h)
        return (ax[0] * s, ax[1] * s, ax[2] * s, math.cos(h))
    return qmul(axis((0, 1, 0), yaw), qmul(axis((1, 0, 0), pitch), axis((0, 0, 1), roll)))


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def mirror(q):
    """a left hand's orientation as the right one's (mirrored across the body's plane, x -> -x)"""
    return (q[0], -q[1], -q[2], q[3])


# the real Quest 3 at rest (Virtual Desktop, user's log: arms hanging, controllers held loosely), head-relative
QUEST_REST_L = ((-0.23, -0.46, -0.35), (-0.547, -0.169, 0.209, -0.793))

# preset: (left (x y z yaw pitch roll) or ('q', pos, quat)), the right one mirrored from it
PRESETS = {
    'ahead': (-0.20, 1.35, -0.40, 0, 0, 0),             # held out ahead, pointing forward
    'ahead_low': (-0.22, 1.15, -0.35, 0, -20, 0),
    'down': (-0.25, 0.95, -0.10, 0, -70, 0),            # arms hanging, controllers pointing forward-down
    'hips': (-0.22, 1.00, -0.25, 0, 0, 0),              # at the hips, pointing forward (a natural hold)
    'up': (-0.25, 1.95, -0.25, 0, 60, 0),               # raised overhead
    'out': (-0.60, 1.40, -0.10, 90, 0, 0),              # arms out to the sides, pointing out
    'chest': (-0.10, 1.40, -0.25, -30, 0, 0),           # in front of the chest, pointing inward
    'roll_in': (-0.20, 1.35, -0.40, 0, 0, -45),         # ahead, wrists turned in (thumbs together)
    'roll_out': (-0.20, 1.35, -0.40, 0, 0, 45),
    'palms_up': (-0.20, 1.30, -0.40, 0, 0, 90),
    'palms_down': (-0.20, 1.30, -0.40, 0, 0, -90),
    'point_up': (-0.20, 1.35, -0.40, 0, 45, 0),
    'point_down': (-0.20, 1.35, -0.40, 0, -45, 0),
    'shoulder': (-0.15, 1.65, 0.10, 0, 0, 0),           # over the shoulder (weapon / shield slot)
    'quest_rest': ('qrel',) + QUEST_REST_L,            # the real Quest pose, at rest
}


def preset_pose(name, h):
    p = PRESETS[name]
    if p[0] == 'qrel':
        pos, q = p[1], p[2]
        pos = (HEAD[0] + pos[0], HEAD[1] + pos[1], HEAD[2] + pos[2])
    else:
        pos, q = p[:3], quat_euler(*p[3:])
    if h == 'right':
        pos, q = (-pos[0], pos[1], pos[2]), mirror(q)
    return pos, q


def png(path, w, h, rgb):
    raw = b''.join(b'\x00' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def ppm_to_png(src, dst):
    for _ in range(100):   # (fake_xr may still be writing it: wait for all of its pixels)
        d = open(src, 'rb').read()
        m = re.match(rb'P6\s+(\d+)\s+(\d+)\s+(\d+)\s', d)
        if m and len(d) >= m.end() + int(m.group(1)) * int(m.group(2)) * 3:
            break
        time.sleep(0.05)
    w, h = int(m.group(1)), int(m.group(2))
    png(dst, w, h, d[m.end():m.end() + w * h * 3])


class Sim:
    def __init__(self, save, out, env, runtime_json=None):
        self.out = os.path.abspath(out)
        os.makedirs(self.out, exist_ok=True)
        self.live = os.path.join(self.out, 'live.txt')
        for p in (self.live, self.live + '.ack'):
            if os.path.exists(p):
                os.remove(p)
        self.seq = 0
        self.state = {}      # the live file's lines by what they set (each write carries the whole state)
        self.vd = runtime_json is not None   # (a real headset: the hands go to the game's SAVAGEWIND_VR_SIM_HANDS file)
        self.simfile = os.path.join(self.out, 'simhands.txt')
        e = {'FAKE_XR_LIVE': self.live, 'SAVAGEWIND_VR_LOG_ARMS': '30', 'FAKE_XR_CAPTURE_EVERY': '0'}
        if self.vd:
            e['SAVAGEWIND_VR_SIM_HANDS'] = self.simfile
            open(self.simfile, 'w').close()
        e.update(env)
        self.game, self.proc, self.log = re_run.boot(save, self.out, e, runtime_json=runtime_json)

    def push(self, extra=(), settle=0.25):
        """write the state (and one-shot lines), wait until fake_xr applied it"""
        self.seq += 1
        if self.vd:   # (relative to the head: the presets' head stands at HEAD)
            out = []
            for k, v in self.state.items():
                if k.startswith('hand '):
                    w = v.split()
                    out.append('handq %s %.4f %.4f %.4f %s' % (w[1], float(w[2]) - HEAD[0], float(w[3]) - HEAD[1],
                                                             float(w[4]) - HEAD[2], ' '.join(w[5:9])))
            with open(self.simfile + '.tmp', 'w') as f:
                f.write('\n'.join(out) + '\n')
            os.replace(self.simfile + '.tmp', self.simfile)
            time.sleep(0.1 + settle)
            return
        lines = ['seq %d' % self.seq] + list(self.state.values()) + list(extra)
        tmp = self.live + '.tmp'
        with open(tmp, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        os.replace(tmp, self.live)
        end = time.time() + 20
        while time.time() < end:
            try:
                if int(open(self.live + '.ack').read().split()[0]) >= self.seq:
                    time.sleep(settle)   # (a few frames for the game to draw it)
                    return
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.03)
        print('  (fake_xr did not apply seq %d)' % self.seq)

    def set_hand(self, h, pos, q):
        self.state['hand ' + h] = 'handq %s %.4f %.4f %.4f %.5f %.5f %.5f %.5f' % ((h,) + tuple(pos) + tuple(q))

    def arms(self):
        text = open(os.path.join(self.out, 'game.log'), 'rb').read().decode('utf-8', 'replace')
        got = re.findall(r'^.*\[vr-(?:arms|hands)\].*$', text, re.M)
        return '\n'.join(got[-3:]) if got else '(no [vr-arms] lines yet)'

    def run(self, line):
        w = shlex.split(line)
        if not w or w[0].startswith('#'):
            return
        c = w[0]
        if c == 'presets':
            print('  ' + ' '.join(sorted(PRESETS)))
        elif c == 'pose':
            sides = ['left', 'right'] if len(w) < 3 or w[2] == 'both' else [w[2]]
            for h in sides:
                self.set_hand(h, *preset_pose(w[1], h))
            self.push()
        elif c == 'hand':
            v = [float(x) for x in w[2:8]]
            self.set_hand(w[1], v[:3], quat_euler(*v[3:]))
            self.push()
        elif c == 'handq':
            v = [float(x) for x in w[2:9]]
            self.set_hand(w[1], v[:3], v[3:])
            self.push()
        elif c == 'rel':
            v = [float(x) for x in w[2:8]]
            yw = math.radians(HEAD[3])
            dx, dz = v[0] * math.cos(yw) + v[2] * math.sin(yw), -v[0] * math.sin(yw) + v[2] * math.cos(yw)
            self.set_hand(w[1], (HEAD[0] + dx, HEAD[1] + v[1], HEAD[2] + dz), quat_euler(HEAD[3] + v[3], v[4], v[5]))
            self.push()
        elif c == 'head':
            HEAD[:] = [float(x) for x in w[1:7]]
            self.state['head'] = 'head ' + ' '.join(w[1:7])
            self.push()
        elif c == 'sweep':
            h, ax, a, b, n = w[1], w[2], float(w[3]), float(w[4]), int(w[5])
            prefix = w[6] if len(w) > 6 else 'sweep_%s_%s' % (h, ax)
            base = self.state.get('hand ' + h)
            pos = [float(x) for x in base.split()[2:5]] if base else list(preset_pose('ahead', h)[0])
            for i in range(n):
                ang = a + (b - a) * i / max(1, n - 1)
                e = {'yaw': (ang, 0, 0), 'pitch': (0, ang, 0), 'roll': (0, 0, ang)}[ax]
                self.set_hand(h, pos, quat_euler(*e))
                self.push()
                time.sleep(0.4)
                self.run('shot %s_%+04d' % (prefix, int(round(ang))))
        elif c in ('grip', 'trigger'):
            path = '/user/hand/%s/input/%s/value' % (w[1], 'squeeze' if c == 'grip' else 'trigger')
            self.state[c + w[1]] = 'value %s %s' % (path, w[2])
            self.push()
        elif c == 'tap':   # tap <grip|trigger> <left|right> [s]: pressed and let go (a short press: under 0.5 s)
            path = '/user/hand/%s/input/%s/value' % (w[2], 'squeeze' if w[1] == 'grip' else 'trigger')
            self.state[w[1] + w[2]] = 'value %s 1' % path
            self.push(settle=0)
            time.sleep(float(w[3]) if len(w) > 3 else 0.15)
            self.state[w[1] + w[2]] = 'value %s 0' % path
            self.push()
        elif c == 'move':  # move <left|right> x y z yaw pitch roll <s>: there smoothly (a swing, a reach)
            h, v, dur = w[1], [float(x) for x in w[2:8]], float(w[8])
            cur = self.state.get('hand ' + h)
            p0 = [float(x) for x in cur.split()[2:5]] if cur else list(preset_pose('ahead', h)[0])
            q0 = [float(x) for x in cur.split()[5:9]] if cur else list(preset_pose('ahead', h)[1])
            q1 = quat_euler(*v[3:])
            if sum(a * b for a, b in zip(q0, q1)) < 0:
                q1 = tuple(-x for x in q1)
            n = max(2, int(dur / 0.03))
            t0 = time.time()
            for i in range(1, n + 1):
                k = i / n
                q = [a * (1 - k) + b * k for a, b in zip(q0, q1)]
                ql = math.sqrt(sum(x * x for x in q))
                self.set_hand(h, [a * (1 - k) + b * k for a, b in zip(p0, v[:3])], [x / ql for x in q])
                self.push(settle=0)
                time.sleep(max(0, t0 + dur * k - time.time()))
            time.sleep(0.25)
        elif c == 'draw':  # the weapon out: the right hand over the right shoulder, a short grip there, back ahead
            self.run('move right 0.15 1.65 0.12 0 0 0 0.4')
            self.run('tap grip right')
            self.run('move right 0.20 1.35 -0.40 0 0 0 0.4')
            time.sleep(1.5)
        elif c in ('focus', 'unfocus'):   # the runtime takes input focus away (the headset off, its menu) / gives it back
            self.push([c])
        elif c == 'button':
            self.state['b' + w[1]] = 'button %s %s' % (w[1], w[2])
            self.push()
        elif c == 'stick':
            self.state['s' + w[1]] = 'stick /user/hand/%s/input/thumbstick %s %s' % (w[1], w[2], w[3])
            self.push()
        elif c == 'shot':
            rel = os.path.relpath(os.path.join(self.out, w[1] + '.png'), re_run.T.TREE).replace('\\', '/')
            self.game.cmd('shot', rel, ok=False)
            print('  ' + os.path.join(self.out, w[1] + '.png'))
        elif c == 'xshot':
            self.push(['shot ' + w[1]])
            time.sleep(0.6)
            cap = os.path.join(self.out, 'cap')
            for f in sorted(os.listdir(cap)):
                if f.startswith(w[1] + '_layer') and f.endswith('.ppm'):
                    ppm_to_png(os.path.join(cap, f), os.path.join(self.out, f[:-4] + '.png'))
                    print('  ' + os.path.join(self.out, f[:-4] + '.png'))
        elif c == 'arms':
            print(self.arms())
        elif c == 'wait':
            time.sleep(float(w[1]))
        elif c == 'game':
            print('  ', self.game.cmd(*w[1:], ok=False))
        else:
            print('  ? ' + line)

    def stop(self):
        perf_routes.stop_game(self.game, self.proc, self.log)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--save', required=True)
    ap.add_argument('--out', default='build/vr/handsim')
    ap.add_argument('--env', action='append', default=[], help='NAME=value for the game')
    ap.add_argument('-i', action='store_true', help='read commands from stdin')
    ap.add_argument('--runtime-json', help='a real runtime instead of fake_xr (its head and hands are then the '
                    "headset's: pose commands do nothing; game commands and shots work)")
    ap.add_argument('cmds', nargs='*')
    a = ap.parse_args()
    sim = Sim(a.save, a.out, dict(kv.split('=', 1) for kv in a.env), a.runtime_json)
    try:
        if not a.runtime_json:
            sim.run('head 0 1.7 0 0 0 0')
        for c in a.cmds:
            print('$ ' + c)
            sim.run(c)
        if a.i:
            for line in sys.stdin:
                print('$ ' + line.strip())
                sim.run(line)
                sys.stdout.flush()
    finally:
        sim.stop()


if __name__ == '__main__':
    main()
