#!/usr/bin/env python3
"""BOTW VR's icon (tools/vr/botwvr.ico, the VR launchers' and the desktop shortcut's): drawn here from plain shapes,
nothing of the game's art - a dusk sky over green hills in a rounded tile, a white VR headset with glowing lenses.

  python tools/vr/make_icon.py [out.ico]     (needs Pillow)
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

S = 512   # drawn large, scaled down for each size


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def draw():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    # the tile: a dusk sky, gold low on the horizon
    sky = Image.new('RGBA', (S, S))
    sd = ImageDraw.Draw(sky)
    for y in range(S):
        t = y / S
        c = lerp((14, 24, 58), (40, 86, 140), min(1, t / 0.55)) if t < 0.55 else lerp((40, 86, 140), (240, 178, 96), (t - 0.55) / 0.45)
        sd.line([(0, y), (S, y)], fill=c + (255,))
    # hills, far to near
    for k, (col, base, amp, f) in enumerate([((56, 120, 88), 0.70, 0.07, 5.0), ((34, 92, 60), 0.80, 0.06, 7.0),
                                             ((20, 62, 40), 0.90, 0.05, 9.0)]):
        pts = [(x, S * base - S * amp * (0.6 * math.sin(x / S * f + k) + 0.4 * math.sin(x / S * f * 2.3 + 2 * k)))
               for x in range(0, S + 8, 8)]
        sd.polygon(pts + [(S, S), (0, S)], fill=col + (255,))
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([8, 8, S - 8, S - 8], radius=110, fill=255)
    im.paste(sky, (0, 0), mask)
    # the headset from the front: a white body and strap, a dark glossy visor with a cyan glow across it
    hd = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(hd)
    d.rectangle([22, 214, 90, 262], fill=(222, 228, 238, 255))          # (the strap, each side)
    d.rectangle([S - 90, 214, S - 22, 262], fill=(222, 228, 238, 255))
    d.rounded_rectangle([62, 140, S - 62, 336], radius=78, fill=(246, 248, 252, 255))
    d.rounded_rectangle([92, 168, S - 92, 308], radius=56, fill=(14, 26, 54, 255))
    glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rounded_rectangle([118, 222, S - 118, 254], radius=16, fill=(80, 220, 255, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(12))
    d.rounded_rectangle([126, 228, S - 126, 248], radius=10, fill=(150, 238, 255, 255))
    d.polygon([(130, 182), (210, 182), (160, 214), (112, 214)], fill=(60, 90, 140, 255))   # (a shine on the visor)
    shadow = hd.split()[3].filter(ImageFilter.GaussianBlur(10))
    im.paste((0, 0, 0, 120), (6, 12), shadow)
    im = Image.alpha_composite(im, hd)
    im = Image.alpha_composite(im, glow)
    return im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'botwvr.ico')
    im = draw()
    im.save(out, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    im.resize((256, 256), Image.LANCZOS).save(os.path.splitext(out)[0] + '.png')
    print(out)


if __name__ == '__main__':
    main()
