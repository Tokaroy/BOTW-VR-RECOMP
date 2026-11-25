# VR performance action plan

*En español (with the original plan in full): [PERFORMANCE-PLAN.es.md](PERFORMANCE-PLAN.es.md)*

*State: in progress. Updated 2026-11-25 (afternoon).*

## Current state (2026-11-25)

Measured on Windows, Ryzen 9 9950X3D (~5.3 GHz effective), RTX 3090 driver 616.92, fake_xr at 500 Hz, eyes 1718x1800,
dev build, Great Plateau, a scratch save, 5 interleaved rounds ([DEVLOG.md](DEVLOG.md)):

| Path | headset fps | x | ms a pair (p95 / p99) | GPU | State |
|---|---|---|---|---|---|
| Stereo (compatibility) | 98.5 | 1.00 | 10.15 (10.4 / 11.0) | 69% | **the default** (Automatic) |
| Multiview | 147.5 | 1.50 | 6.78 (7.3 / 8.0) | 69% | experimental (Options > VR > Rendering: Multiview); the default for a few hours on 2026-11-25, back off after a headset showed smoke, ground and markers in one eye only |
| Mono | 178.6 | 1.81 | 5.60 (5.8 / 6.1) | 64% | only when chosen; never automatic |
| Synchronous stereo (prototype) | 79.6 | 0.81 | 12.56 | 41% | research, hidden (`SAVAGEWIND_VR_SYNC=1`) |

- **Done:** the selector (Options > VR > Rendering, also in the launcher; Automatic picks Stereo for now (Multiview once both eyes match); Mono never automatic); the fallback to Stereo on a driver
  without multiview; smooth turning in multiview (it jumped 0.35 rad at a time) and the view with the hands' anchor;
  Mono checked (the same bytes in both eyes, views from the head's centre, one update a pair); the tools (`vr
  frametimes`, `vr lead`, `test_vr_mono.py`, `test_vr_sun_flare.py`, `--mode` in the tests).
- **Still CPU-bound** in all three (the `nvn-queue` thread busy, GPU 64-69%): foveation or dynamic resolution would not
  help on this PC yet.
- **Open:** PGO against PGO; a real headset (fps, reprojection, `vr lead`, Mono's comfort); a slower CPU (estimated, not
  measured: one at ~70% of the per-thread speed would put Stereo under 72 Hz and Multiview within 90 Hz); in
  multiview, per-object motion vectors, the Upscaler/Sharpening/Colour per eye and the mixed 64x64 reflection passes;
  the sun's flares (a player reports them fixed in 25.2; fake_xr shows a veil and a red streak in VR's default that are
  still to identify); the hands while moving (a 25.2 report: measure `vr lead` in the headset).

## The modes

| Option | What | Rules |
|---|---|---|
| **Automatic (recommended)** | Stereo for now; Multiview once it draws both eyes alike everywhere (then: when the driver supports it and none of Video's Upscaler, Sharpening or Colour is on) | Never picks Mono |
| **Stereo** | A game frame per eye (the path every earlier release used) | The fallback; for A/B and driver trouble |
| **Multiview** | One game update a pair, both eyes drawn into two layers in one pass | Falls back to Stereo on a driver without multiview |
| **Mono (same picture in each eye)** | One centred view for both eyes | No binocular disparity or stereoscopic depth; an accessibility option for people who see with one eye and a speed option; only by explicit choice |

The rest of the plan (baseline per hardware, finishing multiview, mono, correctness before speed, the measuring rules,
the finishing criteria) is in the Spanish document.
