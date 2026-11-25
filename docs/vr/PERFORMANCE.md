# VR performance: how it is measured, where the time goes, and why BetterVR's way is faster

*En español: [PERFORMANCE.es.md](PERFORMANCE.es.md)*

## Why a recomp is not (yet) faster than BetterVR in VR

The game's own code runs natively here, so the simulation is not what limits us. What does is how a stereo frame is
made:

| | Savage Wind VR (`SAVAGEWIND_VR_STEREO=1`, the default) | BetterVR 1.0.1 (Cemu) |
|---|---|---|
| Game frames per headset frame | 2: one per eye (the game at twice the headset's rate) | 1 |
| Each draw's translation to Vulkan (CPU) | twice: once per eye, on one thread (`nvn-queue`) | once |
| Each draw on the GPU | twice: two separate frames | once, into two layers (Vulkan **multiview**: `gl_ViewIndex` picks each eye's camera) |
| Passes that do not depend on the eye (shadow cascades, cube maps) | drawn twice (shadows once is wrong: [DEVLOG](DEVLOG.md) 2026-11-25) | once ("mono sections") |
| Fewer pixels at the edges | no | foveated rendering (its Cemu: `LatteView_RequestFoveation`) |

Measured here (Windows, RTX 3090, fake_xr eyes 1718x1800, the Great Plateau, method below): **~102 headset frames a
second with a dev build, ~114 with the release zip**; the GPU **~70% busy**; the limit is the translating thread,
**~4.9 ms of CPU per game frame** (~3460 draws: descriptor sets 1.36 ms, preparation 1.28 ms, textures 0.71 ms, vertices
0.52 ms; [DEVLOG.es.md](DEVLOG.es.md)). Two of those per headset frame: ~100 pairs a second at most, whatever the GPU.
BetterVR pays its translation once per headset frame.

Not measured here: BetterVR's own frame rate on this machine (it needs Cemu and the Wii U game). The comparison above
is of the architectures; numbers from players with both on the same headset and resolution are welcome.

The synchronous stereo prototype ([SYNC_STEREO.md](SYNC_STEREO.md), `SAVAGEWIND_VR_SYNC=1`) simulates once per pair
but still translates every draw twice (a replay for the right eye), plus its own overhead: 85-87 fps against 102. It
is not the fast path by itself; what it found (which constants hold the camera, which passes depend on the eye) is what
multiview needs.

## The plan: multiview

1. The scene's passes drawn once into two-layer targets with `VkRenderPassMultiviewCreateInfo` (view mask 0b11); the
   targets that depend on the eye are the ones synchronous stereo marks (exec.c `sync_draw_dep`: draws that read the
   camera's rows, or textures drawn by such draws); the rest (shadow cascades, cube maps, compute) stay single-layer and
   are drawn once.
2. The translated shaders (runtime/nvn/maxwell/translate.c) read the camera's rows per view: the scene's cbuf 3 rows
   0-13 (view, view-projection, projection, inverse), 21-34 (the last frame's), 42-53 (the shadow cascades from view
   space), the env block's view and inverse (cbuf 4/5 at +0x2b0), the eye's position: from a second buffer when
   `gl_ViewIndex == 1`, filled with the right eye's values as vr_sync.c's `vr_sync_patch` makes them.
3. Textures sampled from a two-layer target read the draw's own layer (`gl_ViewIndex`).
4. The game at one frame per headset frame (the synchronous stereo's camera: the left eye's, both eyes' fields for
   culling).

Expected (an estimate, not measured): the translation once per pair (~5 ms: a CPU ceiling near 200 pairs a second);
the GPU then the limit, today ~6.9 ms a pair at 70%, less with the shadow cascades and vertex work done once - about
1.4x today's frame rate, GPU-bound.

## How to measure

Everything runs against **fake_xr** (`tools/vr/fake_xr`, built by `make VR=1`: `build/vr/fake_xr.dll`), a headless
OpenXR runtime: no headset, the same frames every time. The tools are in `tools/vr/bench/` (Python 3 with numpy and
Pillow for the pictures):

| Tool | What |
|---|---|
| `bench.py --case NAME --exe EXE --save SAVE [--runs 3] [--env K=V ...]` | frame rate: per run ~12 s in the world at the Great Plateau, then 15 s measured; the median of the runs as `SUMMARY` |
| `bench.py --ab ROUNDS --exe-a A --exe-b B [--env-b K=V]` | A/B interleaved (A, B, A, B...): the GPU's clock and the machine's noise drift over minutes |
| `stereo_depth.py --case NAME --exe EXE --save SAVE [--yaw 37] [--spin] [--walk]` | both eyes captured three times with the hands held ahead; each patch's shift between the eyes and the depth it gives (the hands ~0.54 m, the far mountains ~0) |
| `profile.py --case NAME --exe EXE --save SAVE` | the translating thread's samples by function and line (`--only file.swprof` for a capture already made) |

What the numbers are: **headset fps** = the `vr` control command's `frames` over the measured time (what the player
sees); **game fps** = the `state` command's `frame` (twice the headset's in stereo); **p95** = the `frames 10` command;
**GPU** = nvidia-smi's use of each GPU; **freezes** = log lines `acquire blocked` / `present took` / `a wait for a
submission took` over 100 ms.

Rules learned the hard way:
- **A save of its own for each run**: the tools copy `--save` into the run's folder. Never point them at your saves.
- **Compare like with like**: release zips are built with PGO (`make dist VR=1 DIST_PGO`), ~10% faster than `make VR=1`.
  Dev build against dev build.
- **Variants each in a folder of their own, named `savagewind.exe`**: the game library (`swgame.dll`) imports the
  executable by that name; a renamed copy does not start. Copy `swgame.dll` and `swgame.dll.id` beside it.
- **Interleave and repeat**: single runs vary by 5% (98-109 fps seen on the same build); 3-5 runs interleaved, the median.
- **A capture stalls the game for seconds** (fake_xr writes PPMs): keep captures out of timed runs, and several seconds
  apart.
- **Turn the head off the world's axes** (`--yaw 37`) when checking cameras: axis-aligned views look like identity
  matrices, so searches for the camera find false matches.
- **Compare eyes, not only frames**: a check of one eye between frames missed the right eye's wrong shadows (2026-11-25).
- `SAVAGEWIND_VR_SYNC_LOG=1`, `SAVAGEWIND_VR_SYNC_DUMP=<w>`, `SAVAGEWIND_VR_SYNC_CENSUS=1` and `SAVAGEWIND_VR_SYNC_CHECK=1`
  ([../VR.md](../VR.md)) show what synchronous stereo marks, the constants and GLSL of a pass, where the camera is in the
  constants, and whether the view made from eye/at/up matches the game's.
- The game's code to read: `generated/main/*.c` after `make gen` (functions `f_<address>`); the translated shaders: the
  GLSL `SAVAGEWIND_VR_SYNC_DUMP` writes. A pass's constants come from `cbuf_info` in runtime/nvn/vulkan/exec.c; which
  vec4s a shader reads is `ShaderInfo.cbuf_rows` (runtime/nvn/maxwell/shader.h).
