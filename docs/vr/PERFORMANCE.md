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

The ceiling, measured: mono (`SAVAGEWIND_VR_STEREO=0`: one translation and one picture per headset frame, both
eyes shown the same picture) runs at **173 headset fps** against 102 in stereo (dev build, the GPU at 68%): that is
what translating once per pair is worth on the CPU side. Multiview adds the second view's GPU work back: today a pair
costs the GPU ~6.9 ms (70% at 102), so about 145 pairs a second if nothing else changes, more with the shadow cascades
and vertex work done once. Expected: ~1.4x today's frame rate, GPU-bound.

### Progress

| Step | State |
|---|---|
| The shaders' multiview variant (`ShaderKey.multiview`, runtime/nvn/maxwell/translate.c `cbuf_ref`): cbuf 3 declared twice as long, the left eye's copy then the right eye's, every read at `gl_ViewIndex` x its rows on (`MV_CBUFS`, at most `MV_MAX_ROWS` = 2048 vec4s an eye: both in a 64 KB uniform buffer); `ShaderInfo.mv_cbufs` / `mv_rows` say what to bind | done; `SAVAGEWIND_VK_MV_TEST=1` translates and compiles the variant of every vertex and fragment shader the game uses, unused: 0 failures in ~400 shaders on the Plateau (2026-11-25), ~2/3 of them read cbuf 3 |
| The device with the `multiview` feature (`g_vk.multiview`) | done (a driver without it says so in the log) |
| Pipelines with `VkPipelineRenderingCreateInfo.viewMask` 0b11 | next |
| Textures of two-layer images read at the draw's own layer (`ShaderKey.mv_tex`, translate.c `mv_layer_rewrite`: those slots' samplers made array samplers, every `texture` / `textureLod` / `textureGather` / `texelFetch` given the layer `gl_ViewIndex`, `textureSize` its `.xy`) | done; `SAVAGEWIND_VK_MV_TEST=1` now also reads every 2D slot per eye: 0 failures in ~400 shaders (a sample in mvtest_sample.glsl) |
| Two-layer targets for the passes that depend on the eye (synchronous stereo's marks) | to do |
| The right eye's copy of cbuf 3 filled (vr_sync.c's patch) and bound after the left one | to do |
| The post chain (TAA, the HUD apart, FSR) per layer, each layer to its eye's swapchain | to do |

### The design, piece by piece (for whoever continues it)

1. **Which targets get two layers.** The ones synchronous stereo marks (exec.c `sync_draw_dep`: drawn by a draw that
   reads the camera's rows, or from such a target). Render targets live across frames: once a texture has been marked,
   its image is made again with 2 array layers (as `vk_make_scalable_like` remakes an image at another size,
   textures.c), and stays so. The shadow cascades, cube maps and the like are never marked: one layer, drawn once (the
   GPU's saving).
2. **A pass into two-layer targets is a multiview pass**: `VkRenderingInfo.viewMask` = 0b11 (exec.c `begin_pass`), the
   attachments' views `VK_IMAGE_VIEW_TYPE_2D_ARRAY` over both layers, its pipelines made with the same view mask (part of
   the pipeline's key) and the shaders' multiview variant.
3. **Its constants**: cbuf 3 bound as one buffer of `mv_rows[3]` vec4s for the left eye then as many for the right
   (`ShaderInfo.mv_cbufs`), the right half the left one with the right eye's camera put in (vr_sync.c `vr_sync_patch`:
   view, view-projection, projection, inverse, the last frame's, the shadow cascades from view space). Other cbufs with
   the camera (the env block in cbuf 4/5, the eye's place in cbuf 6) join `MV_CBUFS` the same way when needed.
4. **Textures read in a multiview pass from a two-layer target** read the draw's own layer: the shader's texture slot
   declared as an array texture, its coordinate's layer `gl_ViewIndex` - a per-slot mask in the shader key (which slots
   are two-layer at that draw). Outside multiview passes (the runtime's post chain, a copy for the CPU) a two-layer
   texture is read through a 2D view of one layer: the eye being finished.
5. **Clears and copies** into a two-layer target cover both layers; a copy from a two-layer texture into a one-layer one
   (a readback, the HUD-less copy) takes the layer of the eye being finished.
6. **The frame**: the game as synchronous stereo has it (one game frame per pair, the left eye's camera; the right
   eye's camera and field made in the same update, vr_camera.c `vr_sync_frame`). At the present (device.c
   `backend_present`): the post chain (TAA per eye, the HUD apart, FSR, `vk_vr_images`) run for layer 0 and presented
   as the left eye, then for layer 1 as the right eye - the second present synchronous stereo already makes, with no
   replay of the lists.
7. **Not two-layer and depending on the eye**: anything the marks miss would come out the same in both eyes - the
   marks' log (`SAVAGEWIND_VR_SYNC_LOG=1`) and `stereo_depth.py` (the far patch at 0 px, the hands at ~0.54 m) are the
   checks.

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
