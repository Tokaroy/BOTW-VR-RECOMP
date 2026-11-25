# BOTW VR: development log

*En español (with every measurement in full): [DEVLOG.es.md](DEVLOG.es.md)*

What was done, how it was tested and what is left, newest first. Settings and tests: [../VR.md](../VR.md); reverse
engineering: [re-notes.md](re-notes.md); the state of every feature: [FEATURES.md](FEATURES.md).

## 2026-11-25 (Options > VR > Rendering: Multiview by default; Mono; multiview's turning fixed)

- **Options > VR > Rendering** (also on Savage Wind Configuration's VR tab; `SAVAGEWIND_VR_RENDER`; after a restart):
  **Automatic** (the default), Stereo, Multiview, Mono. Automatic picks Multiview when the driver has it and Video's
  Upscaler, Sharpening and Colour are off (multiview does not apply them yet), else Stereo. Mono is never picked by
  itself. The log says which ran (`[vr] rendering: ...`); the older variables still win. In all 13 languages.
- **Turning with the stick in multiview went in 0.35 rad (~20 degree) jumps**: stereo's "the left frame keeps the
  heading its skeleton was placed with, the right one takes the new" ran on every multiview frame, which has no right
  frame - the view stood still until 0.35 rad and jumped. Those were also the 18 of ~210 frames with the view against
  the hands' anchor. Now at most 1.9 degree steps and 0 of 219 frames apart; test_vr_stereo_sync.py checks it.
- **A player on 25.2**: flares fixed; arms "not correctly updated when moving". With multiview's variables the jumps
  above explain it; otherwise `vr lead` (new) in a headset says how far the hands trail (fake_xr gives 0 ms).
- Final build, 3 interleaved runs: **the default (Multiview) 144.3 headset fps against 94.5 in Stereo**, pair p95/p99
  7.6/8.1 ms against 11.6/12.2, no freezes. The whole VR suite in the default mode passes but `window`, `eye_res` and
  test_vr_game's `headtrack`, which fail alike on the previous build (78d98a5) and in Stereo. Automatic uses Stereo when
  the eyes' depth is asked for (`SAVAGEWIND_VR_DEPTH=1`: multiview does not attach it yet); `camera` reads the game's
  camera in multiview (TAA's stood still).
- macOS: the disk image workflow takes a vr-* tag to attach to; no OpenXR runtime on macOS, so it plays flat.

## 2026-11-25 (performance audit: the four modes measured; test hooks for what was left open)

- Windows, Ryzen 9 9950X3D (~5.3 GHz effective), RTX 3090 driver 616.92, fake_xr 500 Hz, eyes 1718x1800, dev build of
  78d98a5, Great Plateau, a scratch save, 5 interleaved rounds: **normal stereo 98.5 headset fps, multiview 147.5
  (1.50x), mono 178.6 (1.81x), synchronous stereo alone 79.6 (0.81x)**; GPU 64-69% (41% for the prototype); the
  translating thread busy in every mode: still CPU-bound. Not measured: PGO builds, a real headset, a slower CPU.
- **The numbers that compare between modes**: `state`'s frame counts presents, not game updates (multiview presents
  twice a pair), so the old p95 was bimodal there. New: `vr frametimes [s]` (the times between headset frames: a pair
  each) and bench.py's pair p95/p99, camera updates a pair (6 in normal stereo, 3 with multiview or mono: one game
  update a pair, measured), the mode, CPU and driver in each result. Pair p95/p99: normal stereo 10.4 / 11.0 ms (the
  edge of 90 Hz's 11.1), multiview 7.3 / 8.0, mono 5.8 / 6.1.
- **Fallback**: multiview asked for on a driver without it used to leave the synchronous stereo prototype on; now VR
  falls back to normal stereo (`SAVAGEWIND_VK_NO_MULTIVIEW=1` runs as on such a driver: normal stereo, 100 fps).
- **Mono** (`test_vr_mono.py --control`): both eyes the same bytes, both views submitted from the head's centre (0.0 mm;
  normal stereo ±31.5 mm), one symmetric field (±0.942 rad: ~20% fewer pixels a degree than an eye), one game update a
  pair. Comfort and its use for people with one working eye need a person in a headset.
- **Multiview still fails** `test_vr_stereo_sync.py --mode multiview`: turning with the stick, 18 of ~210 frames have
  the view turned against the hands' anchor (normal stereo 0 of 288) - three runs alike. `test_vr_taa.py --mode
  multiview` passes.
- **Sun flares** (a player's report on 2026-11-25.1: seen though off, flat): `test_vr_sun_flare.py` shows VR's default
  (flares off) with a milky veil over the picture and a thin red diagonal streak that `SAVAGEWIND_VR_LENS_FLARE=1` also
  has; what draws them is not found yet (next: the passes' shaders with `SAVAGEWIND_LOG_NEW_FS`). A lead, not a
  reproduction of the report.

## 2026-11-25 (multiview: TAA per eye; 145 fps against 100 with TAA)

- Each eye gets its own TAA at the scene's composite (its camera from vr_sync.c, its history, its output over its layer
  of the scene). Default settings: 144.9 headset fps against 100.2 in normal stereo, both with TAA; depth unchanged, no
  ghosting seen turning. Next: object motion vectors in multiview passes, the runtime's post effects per eye, a real
  headset. Details in [PERFORMANCE.md](PERFORMANCE.md).

## 2026-11-25 (multiview: the HUD apart per eye; 150 fps with the default settings)

- The HUD-less copy is made of each layer and kept for the right eye's present; multiview puts SMAA in place of TAA by
  itself. Default settings: 150.5 headset fps against 98.3 in normal stereo with TAA and 104.3 with SMAA, the depth and
  the HUD layer as normal stereo's. Next: TAA per layer, a real headset. Details in [PERFORMANCE.md](PERFORMANCE.md).

## 2026-11-25 (multiview working: 150 headset fps against 104)

- `SAVAGEWIND_VR_SYNC=1 SAVAGEWIND_VR_MV=1` (for now with `SAVAGEWIND_VR_TAA=0 SAVAGEWIND_VR_HUD=0`): both eyes drawn in
  one pass from one game frame, 150 headset fps against 104 in normal stereo (fake_xr, RTX 3090, dev builds), the depth
  of the hands and the far patch as normal stereo's. Fixed on the way: per-eye texture slots bound as 2D views of layer
  0 (both eyes the same), mixed passes with a 2D array (the right eye black), a 64 KB per-eye copy per draw, and a
  `getenv` per draw (40% of the translating thread). Next: the HUD apart and TAA per layer. Details in
  [PERFORMANCE.md](PERFORMANCE.md) and [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-25 (multiview: the ceiling measured, the shaders' multiview variant)

- Mono (one translation per headset frame) runs at 173 headset fps against 102 in stereo: what translating once per
  pair is worth. The shaders' multiview variant (cbuf 3 per eye, read at `gl_ViewIndex`) compiles for all ~400 shaders
  the game used (`SAVAGEWIND_VK_MV_TEST=1`). Details in [PERFORMANCE.md](PERFORMANCE.md).

## 2026-11-25 (why below BetterVR; the measuring tools in the repository)

- In stereo each headset frame is two whole game frames and every draw is translated twice on one thread (~4.9 ms of CPU
  a game frame): ~100 pairs a second at most, the GPU at 70%. BetterVR draws each thing once into two layers (Vulkan
  multiview), once per headset frame. The plan is multiview here; tools and method in [PERFORMANCE.md](PERFORMANCE.md).

## 2026-11-25 (synchronous stereo: the right eye's shadows)

- The shadow pass reads the cascade matrices from view space at rows 42-53 of the context block (S V^-1), the last
  frame's camera at rows 21-34. In the right pass both go to the right eye's view space (M D^-1, D V).
- With SMAA the right eye now matches normal stereo but for one black far tree; about one shot in six still has a
  darker right eye. Details in [DEVLOG.es.md](DEVLOG.es.md) and [SYNC_STEREO.md](SYNC_STEREO.md).

## 2026-11-25 (synchronous stereo: mono passes)

- The left pass marks the targets of draws that read the camera (the exact vec4 rows) or marked textures; the right
  pass runs only draws, clears and copies into marked targets. A texture read by a marked draw and written again later
  is marked too (the shadow map, drawn cascade by cascade): without it the right eye was all in shadow.
- The left eye is as in normal stereo, the hands' depth and the far patch match it; left in the right eye: the sun's
  shadows (the view-space shadow matrix is the left eye's) and one far tree. Headset 85-87 fps against 102. Details in
  [DEVLOG.es.md](DEVLOG.es.md) and [SYNC_STEREO.md](SYNC_STEREO.md).

## 2026-11-25 (synchronous stereo: both eyes from one game frame, a first prototype)

- BetterVR 1.0.1's way begun ([SYNC_STEREO.md](SYNC_STEREO.md)): a census of the camera in the constant buffers
  (cbuf 3: view, view-projection, projection, inverse view, as BetterVR's slots 0-3), and `SAVAGEWIND_VR_SYNC=1` (off
  by default): every game frame is the left eye; at its present the translator runs the frame's lists (copied as they
  ran) again with the right eye's camera patched into the constant buffers and presents that as the right eye.
- The right eye's picture is right in its geometry; the light is wrong in both eyes (the second run redraws passes that
  keep state or do not depend on the eye). Headset 103 -> 87 fps. Next: passes drawn once, per-eye state, the
  view-space shadow matrices and lights. Details in [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-25 (both eyes at the same game moment: tried, not possible yet)

- Each eye is a whole game frame and the right one is half a step later (5.6 ms of game time at 90 pairs; Link running
  moves ~2.8 cm between the eyes). The camera already looks from the same place in both.
- **No game time in the right frame** (`SAVAGEWIND_VR_PAIR_SECOND=0.000001`): the stick turn went wrong and the game
  crashed in its own code after ~20 s. Like the 5% / 0.001 tries of 2026-11-20: the game divides by the step and counts
  frames. Dropped.
- **The right frame only drawing:** needs the game loop's calc skipped in right frames and the right eye's camera
  matrices (and shadow cascades) rebuilt before the draw; where calc and draw split was not found without the Ghidra
  project. Not tried.
- **BetterVR 1.0.1's way:** one game frame, every draw repeated for both eyes with each eye's camera constants
  (~2200 lines of game hooks plus emulator changes). The right path here too (the translating thread drawing each scene
  pass twice), and half the simulation; weeks of work, not started. Details in [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-25 (a tester's report: the right eye's shadows, the hands crossed while turning)

- **Shadows once a pair (O13) off by default:** reproduced at Hebra (the right eye's dome dark, shadows moved): the game
  fits the cascades to each frame's camera, so the right eye read the left's maps through its own matrices. ~4-6%
  headset fps. `SAVAGEWIND_VR_SHADOWS_ONCE=1`: on.
- **Hands while turning (B11):** the right frame is drawn with the left's anchor, but the game sometimes calculates
  Link's skeleton after the frame's camera, with the right frame's fresh anchor: turning, the hands showed at ~0.7 m
  instead of 0.54 (2 degrees off in the right eye). `vr_tracking_to_world` now uses the pair's anchor in a right frame:
  0.51-0.54 m turning, the world unchanged. Details in [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-25 (VR performance, Windows: the HUD once a pair, fewer questions a draw)

Measured as the entry below, with development builds (no release PGO), 4 interleaved runs a case: **103.8 -> 108.0
headset fps (+4%)**, p95 5.65 -> 5.34 ms.
- **The game's HUD only in the right eye's frame (O16):** the left eye gets its frame's HUD-less copy and the HUD layer
  comes from the right frame, so the left frame's draws into the composite's image after that copy (~85) reached
  nothing; they now return at once. 103.8 -> 105.6; the HUD layer the same. `SAVAGEWIND_VR_HUD_ONCE=0`: as before.
- **Whether the HUD goes apart, asked once a frame** instead of twice a draw (`vr_world_view`, ~7000 times a frame), and
  the DOF draw's shader compared first: 105.3 -> 108.0.
- `test_vr_game.py` cinema, hud, menus, stereo, scope, exit pass; firstperson's crouch check fails with the 100% save
  with or without these changes. Details in [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-25 (Windows: VR performance measured)

The Windows zips of vr-2026.11.24.3 and vr-2026.11.24.6 against fake_xr (`FAKE_XR_HZ=500`, uncapped;
`SAVAGEWIND_VR_STEREO=1`; 1718x1800 eyes; RTX 3090, driver 616.92; the 100% save at the Great Plateau; ~12 s in the
world, 15 s measured). Median of 3 runs (5 for .6 and its variables, interleaved).

| Case | Headset fps | Game fps | p95 | GPU % | Freezes |
|---|---|---|---|---|---|
| .3, hidden window | 88.4 | 176.8 | 6.57 ms | 79 | 0 |
| .6, hidden window | **113.8** | 227.5 | 5.16 ms | 77 | 0 |
| .6 + `SAVAGEWIND_VR_SHADOWS_ONCE=0` | 109.5 | 219.0 | 5.19 ms | 75 | 0 |
| .6 + `SAVAGEWIND_VK_BARRIER_FRAG=0` | 112.6 | 225.2 | 5.18 ms | 77 | 0 |
| .6 + `SAVAGEWIND_VR_MIRROR=1` | 113.6 | 227.3 | 5.15 ms | 75 | 0 |
| .3, visible window | 95.7 | 191.4 | 6.12 ms | 78 | 0 |
| .6, visible window | 112.6 | 225.4 | 5.19 ms | 76 | 0 |

- **.3 -> .6: 88 -> 114 headset fps (+29%) hidden, 96 -> 113 (+18%) visible**, about Linux's gain even though Windows
  already had the geometry in video memory. Shadows once a pair (O13) is worth ~4%, fragment-only barriers (O12) ~1%
  (noise), the mirror (O11) nothing on Windows. No freeze over 100 ms in any run.
- .6's log: `presents on a thread of their own (second queue)` on the RTX 3090 (Ampere).
- Flicker (O13), Hebra tower, 3 pairs of `shot <tag> 2`: the left eye jumps to ~3.5% changed pixels with and without
  `SAVAGEWIND_VR_SHADOWS_ONCE=0` (edges: TAA jitter after each capture's ~7 s stall), the right eye 0.5-1.1%: no
  shadow flicker. Details in [DEVLOG.es.md](DEVLOG.es.md).

## 2026-11-24 (VR performance: the mirror window, the HUD, the pass barriers)

Measured in fake_xr with the player's settings (1718x1800 eyes, RTX 3090, the 100% save at the Great Plateau,
uncapped headset), median of 3 runs: **85 -> ~111 headset fps** (171 -> ~222 game frames a second, one per eye), and
no more 2 s freezes. Where a frame went first: the GPU 94-96% busy (5.7 ms an eye), the translating thread 100%; at
1080-line eyes only 14% faster, so most of the cost is per frame, not per pixel.
- **The mirror window held the headset up.** On X11 `vkQueuePresentKHR` for the window sometimes took 2 s (more often
  while the window is moved, or when it is not shown), and the game's submissions, the headset's included, waited
  behind it: 2 s freezes in half the runs. In play the headset takes the game's own image, so the window is no longer
  acquired nor presented then (`vr_headless_frame`); it is still on the virtual screen (menus, loading), where the
  headset needs it. `SAVAGEWIND_VR_MIRROR=1` shows it in play (at most at the monitor's rate, the left eye's frames left
  alone). Presenting it from a second queue and thread was tried (VR uses them now, not on NVIDIA before Turing): the
  driver still held the submissions. Window shown: 83.2 -> 86.7 fps with the mirror limited, no freezes without it.
- **The HUD alone** (`vr_hud.frag`) is made only from the right eye's frame, which builds the headset's frame: 86.7 ->
  88.8.
- **Pass barriers:** each pass began behind an all-commands barrier, so no pass overlapped the one before (~200 passes
  a frame, most tiny). In VR they now hold back only the fragment work, as on Mali: a pass whose draws' vertex stage
  reads textures or memory, and any pass after copies, dispatches or memory stores, still waits for everything
  (`SAVAGEWIND_VK_BARRIER_FRAG=0`: as before). 88.8 -> 96; captures of the Plateau and Hebra the same.
- **The guest heap's geometry in video memory on Linux.** The Vulkan backend keeps a copy of the heap's geometry
  pages in video memory and refreshes the ones the CPU wrote (its "heap copy"), but only Windows said which pages were
  written (MEM_WRITE_WATCH), so on Linux every vertex and index fetch read system memory across PCIe. Linux 6.7+ now
  tracks them as Wine's GetWriteWatch does: the guest window registered with a userfaultfd in asynchronous
  write-protect mode, PAGEMAP_SCAN listing the written pages and protecting them again (`runtime/platform/linux.c`;
  `SAVAGEWIND_NO_WRITE_WATCH=1` or an older kernel: as before). The copy turns itself on for discrete GPUs: **95.6 ->
  107 headset fps** (GPU 96% -> ~80% busy); flat at 1280x720 the same 225 fps. Captures of the Plateau and Hebra the
  same; `test_vr_game.py` cinema, hud, stereo, menus, firstperson, scope, weapon and exit pass.
- **The right eye's sun shadows taken from the left frame, now by default.** It was off for flickering. The cause: the
  frame's eye was asked of `vr_frame_eye` (the frame the game is setting up), while the passes are translated a frame
  behind, so it was the left eye's shadows that were left out, in every frame (checked: 42 of 42 frames wrong at the
  shadow passes, 0 with the new `vr_translating_eye`, the oldest frame marked for present and not taken yet; when not
  marked yet, the eye after the last presented). TAA's per-eye history used the same wrong eye (consistently, so
  harmless; now 2949 of 2949 right). Flicker measured with `shot <tag> <n>` (a new fake_xr command for frames in a
  row) at Hebra: 0.07-0.16% of pixels changing between frames with or without. Draws into a pass that is not begun now
  return at once. 108 -> ~111-114 fps. `SAVAGEWIND_VR_SHADOWS_ONCE=0`: both frames draw them.
- Tried and left: no barriers for the terrain's G-buffer reads (+2%).
- `test_vr_game.py stereo` now starts facing the sun (the start view changed with the UI cameras' fix): its image
  comparison sometimes finds no shift (dx 0) though the eyes differ (captures checked); hud, menus pass. The costly compute dispatch (16x1x1, 0.3 ms) is a long straight-line shader with few threads:
  the game's own.
- `tools`: none of these are in a test yet; `test_vr_game.py` cinema, hud, stereo, menus, scope and exit pass.

## 2026-11-24 (the item windows and the inventory in VR; a quick menu's stick turn)

- **I04, the item windows small and off to a side** (a chest's item box far up to the left, the inventory's item
  description small inside a slot, the hearts and page names squeezed to the right): two causes. The VR camera hook
  (`vr_camera_lookat`) took the UI layouts' cameras (ui2d: the eye on the z axis looking at the origin, PauseMenuInfo's at
  0, 0, 989; others at 0, 0, 10 in play) for the world's and gave them the head: PauseMenuInfo's root pane was seen at
  1040, -252, -1810 instead of 0, 0, -989 (read from the game's memory, flat against VR). They are left alone now, and
  no longer set the game's view between the world camera's updates. And a UI projection made in play with the tall eye
  picture's shape was drawn in a 16:9 menu: in VR the UI's projections stay 16:9 (`rt_persp`), hud_patch fits them to the
  picture. Checked in fake_xr: the inventory as in flat play; `test_vr_game.py` hud and menus pass. Validated in the
  headset.
- **C35, a quick menu turned the view on closing:** the right stick picks in it, and the game's camera turned with the
  push; the menu is on the virtual screen, where the camera hook returns early, so the whole turn came in the first
  update after it closed. A menu seen up is remembered there, and the camera's turns are kept from the view while it is
  up and for 0.5 s after (`[vr] quick menu: the camera's turn of N deg kept from the view`). Validated in the headset.
- `test_vr_game.py` firstperson: walking back with the head turned now goes the way the real view looks; at the test
  save's spot that is off a ledge, and the crouch check that follows fails (Link falling, not crouched). Crouching on
  flat ground: the eye 1.55 -> 0.87 m.
- **U07, bombs thrown with the right trigger fell at his feet** (round ones always, square ones often): a rune's bomb
  in hand does not go through the grab action, so the carrying flag the trigger's throw looks at (+ 0xc40 bit 17) stayed
  off and the trigger sent A, the game's "Drop". Found by diffing the player object with a bomb out (fake_xr): + 0xd44
  reads "Bomb" while one is held ("None" otherwise; bit 13 of + 0xc48 with it). `vr_player_carrying` counts it: the
  trigger's release throws (R), round and square, both left his hands with nothing at his feet. Back to untested in
  the headset.
- **Then thrown to a side (headset):** the game's own throw goes along Link's facing, and in first person his body is
  turned to the view only as drawn. Without a swing (the hand under 0.8 m/s) the throw's ground part is now turned to
  the view's heading, its speed and rise kept (`[vr] throw: the game's, turned to the view`). fake_xr, the head turned
  90 deg: both bombs turned -88 deg to the view. With a swing the hand's own velocity still decides (I02).

## 2026-11-24 (headset tests: the start screen's controllers, the eyes apart turning the head)

- **The start screen in the headset took no controller input:** the VR controllers only reached the game. The
  configuration now reads them itself (`vr_menu_pad`: its own action sync, none of the game's mapping or gestures, which
  read the game and crashed the screen when tried) and passes them as a gamepad: A activates, B goes back, either stick
  moves, the triggers change tabs. ImGui's SDL backend clears the gamepad flag each frame without an SDL gamepad, so the
  configuration sets it again after it. Checked against fake_xr: A on PLAY starts the game, kept open or not.
- **Turning the head fast, the eyes apart (WiVRn):** each eye's frame located the head again, a frame apart, and the
  display time it asked for could differ by a refresh; a runtime that reprojects the pair as one head pose showed the
  eyes turned apart. The pair's eyes now come from the left frame's one `xrLocateViews` (with its anchor; the same
  `SAVAGEWIND_VR_PAIR_ANCHOR=0` restores both). fake_xr has `FAKE_XR_HEAD_SPIN=<deg/s>` (the head's yaw at the time
  asked for); `test_vr_stereo_sync.py` at 180 deg/s with eyes 0 m apart: before 8 samples (about 2.3 deg) sideways,
  now 0.
- **Turning smoothly with the stick, crossed eyes on near things:** Link's arms and what they hold are placed before the
  frame's camera, with the anchor the last camera left; a left frame taking a fresh heading drew them a game frame of
  the turn off its own view, in that eye only (the right one draws with the left's anchor). A pair's left frame now
  keeps the heading its skeleton used; the right frame takes the fresh one for the next pair. The `vr` command counts
  `anchor_mismatch`: 0 of 249 frames turning, 240 of 250 with `SAVAGEWIND_VR_PAIR_ANCHOR=0`.
- **Charged attacks (Quest layout):** holding the right trigger opened the weapons' menu after 0.6 s, so no charged
  attack. With the weapon already out the trigger now holds Y as long as it is held; with the shield out the left
  trigger is a guard held as long as wanted. Their menus by trigger stay for empty hands; the shoulders' grips open them
  anytime (BetterVR's way). `test_vr_gestures` 168 checks.
- **Then BetterVR's triggers by default:** the triggers held never open a menu, empty hands too (the right one takes the
  weapon out and charges); the quick menus are the shoulders' grips only. `SAVAGEWIND_VR_TRIGGER_MENUS=1` brings the
  trigger menus back for empty hands. The controls guide and C09 / C11 say so, in every language. 171 checks.
- **The quick menus by the shoulders (headset report):** the left shoulder's grip held with no weapon out sent the
  d-pad's right alone, which the game takes as the weapons' menu (the bows' needs the bow drawn: ZR with it); it now
  goes as the bow grip's menu. The no-head-shake filter no longer drops a quick menu's ZR. With snap or head-only
  turning the right stick's sideways push was kept for turning, so nothing could be picked in a quick menu; while one
  is open the stick goes to the game. 173 checks.
- **The frame rate shown in VR:** the overlay counted game frames, one eye each, so it read twice what the headset
  shows. In VR it counts the headset's frames (one a stereo pair; fake_xr: overlay 100.3 fps, headset 100.0 frames/s),
  and the Dynamic resolution aims at the headset's refresh, not the monitor's. A no longer parries while the raised
  left hand guards (Quest layout).

## 2026-11-24 (the configuration kept open while playing)

- **Settings > Keep open while playing** (on by default; not on macOS nor in Steam's Gaming Mode): PLAY lets the
  start screen's headset session go, the program restarts as Savage Wind Configuration alone (`SAVAGEWIND_LIVE=1`, VR
  off; the same process on Linux, so an AppImage stays mounted) and starts the game in a process of its own. Closing the
  configuration leaves the game running (on Linux it waits for it, hidden).
- **Live settings:** the game reads `savagewind.ini` every half second (by its content) and applies each changed setting
  of `set`'s table, as `set` does (`control_settings.c` control_settings_live): the VR page, render scale, upscaler,
  overlay... Not the window's size or fullscreen, nor what needs a restart. The configuration also reads the file again
  when the game's own menu writes it. Its VR page shows the headset's rows while the game runs in VR.
- **A VR tab in Savage Wind Configuration's Settings** (between Video and Audio): the VR page's rows, so they can be
  set before playing or, the configuration kept open, while playing. What is changed there is saved at once (at most
  five times a second) for the game to pick up.
- The control and companion sockets are no longer inherited (a restarted start screen kept the game's port).
- **Checked:** `tools/vr/test_vr_live_launcher.py` (fake_xr): PLAY, the configuration restarted as `--config`, the game
  in its own process with the headset (343 world frames in 2 s), a change to the file applied live (eye separation 85,
  eye resolution 1080), the configuration still open after the game exits. Windows builds but is not run here.

## 2026-11-24 (Steam Frame report: one eye out of step, crossed eyes)

- **The report:** the right eye often looked out of step with the left, and near things gave a crossed-eyes effect.
- **The cause:** each eye is drawn in its own game frame, half a step apart, and each frame rebuilt the anchor (tracking
  space -> the game's world) from that frame's camera: the turn stick's turn, the game camera's swing, Link's step and
  the eye's place ahead of his head all moved between the eyes, while the headset is only told each eye's tracked
  pose. A turn showed as one eye turned against the other; a step as a false depth.
- **The fix** (`vr_camera.c`): the right frame draws with its left frame's anchor, so both eyes look from one place; the
  hands and roomscale keep the fresh anchor. The compositor now gets each eye's tracked pose, not the one moved by the
  Eye separation option. `SAVAGEWIND_VR_PAIR_ANCHOR=0`: as before, to compare. Things that move in the world (Link
  included) still show their half step.
- **Checked** with a new test, `tools/vr/test_vr_stereo_sync.py` (eyes 0 m apart, so both pictures must match): with the
  right stick held, before 2-3 samples (0.6-0.9 deg) sideways between the eyes, now 0; still, 0 both ways.
  `test_vr_eye_res.py` (1080 / 2160 / 1440 live) and `test_vr_fixed_window.py` (1280x720 window) pass; the stereo,
  first-person, HUD, snap, motion, walk and arms scenarios pass (the stereo pair count failed once during capture
  stalls and passed on a rerun). Not yet seen in a headset.

## 2026-11-23 (arm rigging report)

- The player reports that the wrists follow the controllers, but Link's arm poses look unnatural when moving or turning
  the hands (B01: partly implemented, failed in the headset). In `vr_skel.c::solve_arm`, the elbow pole follows hand
  orientation (`SAVAGEWIND_VR_ELBOW_FOLLOW`, default 3), and the wrist target has a 5 cm offset along the controller's
  back. Compare movement and rotation separately in the hand simulator and headset before changing either; this is a
  likely place to investigate, not a confirmed cause.

## 2026-11-23 (live performance on the VR page; ladders)

- **Eye resolution live (V08):** the game draws at the eyes' size whatever the window (the Steam Frame fix), so
  changing the size is enough: a change of Options > VR > Eye resolution (or `set vr_eye_resolution`) applies the
  next frame and the headset's swapchains follow (`tools/vr/test_vr_eye_res.py`: 1080, 2160 and back to 1440 in
  play, the eyes never stopping). The VR options' range for `set` is now 0-4096 (it stopped at 400).
- **Performance on the VR page (V18):** the FPS overlay, Render scale, Upscaler, its mode (Dynamic included: smaller
  when frames are slow) and Anti-aliasing, the Video pages' own rows, next to the eye resolution.
- **Ladders (C34):** on one (the move flags' bit 4 alone) the walk stick is turned from the view's way to Link's, as
  BetterVR's hook_FixLadder, so forward climbs whatever the player looks at. The turn's sign checked on flat ground
  (`tools/vr/test_vr_ladder.py`, `SAVAGEWIND_VR_LADDER_TEST=1`: forward walks along Link, cos 1.00, not the view;
  without it, toward the view, cos 1.00); not yet on a real ladder (none near the test save).
- **G14** is likely not needed: BetterVR sets the guard's direction from Link's facing, and here Link turns to the
  view to guard. To check in the headset.

## 2026-11-23 (B10: the arm rig)

- **The player's report:** in the headset the wrists followed the hands but the arms took unnatural poses. A view of
  Link from outside while the arms are solved in first person (`SAVAGEWIND_VR_DEBUG_CAM="<back> <right> <up>"`) and a
  pose test (`tools/vr/test_vr_arm_rig.py`: ten poses, the right wrist turned -150..150 deg) measured the first rig:
  the elbow's hint followed the controller's whole turn; the elbow was kept under the shoulder; the shoulders never
  moved; the forearm's roll was taken as solved each frame (no continuity, no limit).
- **The new rig** (`SAVAGEWIND_VR_ARM_RIG=0`: the first, to compare): the elbow's hint as BetterVR's (down, out, a
  little back with the body) plus where the controller points from - its direction only, never its roll - smoothed
  over 0.1 s; the elbow may rise over the shoulder with the hands overhead; the clavicles turn with a hand raised or
  reaching far from chest height up (at most 20 deg, never with the arms hanging); the forearm's roll kept continuous
  from frame to frame (a pause keeps it), eased into 110 deg either way and back to the principal angle past 210.
- In the simulator: every pose solved (0.000 m), the elbow within 5 cm over the whole wrist turn, the roll's steps
  under 40 deg (no flip), the clavicles 20 deg and the elbows over the shoulders overhead, no tunic in the view.
  Not yet seen in the headset.

## 2026-11-23 (the arms' reach; HUD markers and the stamina wheel on the floating HUD)

- **P11, swimming:** played at Zora's Domain (`tools/vr/play_water.py`, flags 0x410): the eye picture shows the water
  surface from just above it, Link's head followed down.
- **Left for later:** C34 (ladders: the move flags 0x10 / 0x12 tell a ladder, but the stick's turn on one can't be
  checked without placing Link on a ladder in the simulator) and G14 (the guard aimed by the hand: the game's guard
  direction is not found yet).
- **Arms:** the first-person eye 4 cm further ahead (22 cm) took the hands 4 cm further from Link's shoulders, past the
  12 cm the IK may stretch an arm at full reach (`test_vr_game.py` arms: 2.3 cm short). The stretch is now 16 cm:
  0.000 m short.
- **H10, markers on the floating HUD:** the UI's world-to-screen (1.9.0 main+0xe1dde0, found from sead's
  Projection::cameraPosToScreenPos at main+0xeb44f8, its only caller in play) is patched where it loads the result
  (site `ui_project`, main+0xe1de34). Labels and markers are drawn for the eye's whole field (45-50 degrees each
  side) but the HUD panel covers about 30: they went toward the centre (an enemy 30 degrees off showed at 17). Each
  now goes where the eye's line to it crosses the panel, as BetterVR's hook_PlaceScreenMarker (HUD following the
  gaze; `SAVAGEWIND_VR_UI_PROJECT=0` turns it off). A new site: the game code is built again on the first start.
- **H11, the stamina wheel:** its caller (main+0xe1ad80) asks for a spot 1.8 m above Link's feet, in his head in
  first person; there it stays under the hearts (layout -482, +170, as BetterVR). Checked against fake_xr by the
  counters (`vr`: ui_stamina, ui_projected); the wheel itself not yet seen in a capture (the test save's stamina full).

## 2026-11-22 (Steam Frame: the world pixelated and the eyes not fusing)

- A tester on Steam Frame standalone (the aarch64 AppImage): the world stayed coarse whatever the eye resolution or
  render scale (menus sharp), and the eyes did not fuse (eyestrain). The cause: the system keeps the game's window at
  its own size there, and the game drew the world at that size, with the camera's frustum given the window's shape
  instead of the eye picture's. Now the game draws at the eyes' size whatever the window (device.c, the window shows
  that image scaled to fit), the frustum takes the eye picture's shape (xr_vulkan.c), and with the HUD on the picture
  the eyes get a copy of the game's image, not the window (exec.c).
- Checked against fake_xr with the window held at 1280x720 (`tools/vr/test_vr_fixed_window.py`): the game draws
  1374x1440, the eyes' swapchains are 1374x1440 and the stereo shift is the same as with a headset-shaped window
  (dx -3); before, 1280x720 and the shift doubled (dx -6). Not yet seen on the Frame itself.
- The suite after merging the release's branch: 19 of 20 pass (crouch, the pause menus and `swing_hits` failed once
  and passed on a rerun). Left: `test_vr_game.py` arms, each wrist 2.1-2.3 cm from its controller against a 2 cm
  limit, the same without this change (it passed before the merge).
- The work left uncommitted (Snapdragon GSR, the overlay on a held menu button, 1440-line eyes) reviewed, its eye
  resolution option fixed (picking 1080 stored the 1440 default), translated into the 12 other languages, committed.

## 2026-11-22 (Savage Wind Beta 1 fixes, BetterVR 1.0.2, the PC Maker; release vr-2026.11.22)

- **Upstream:** Savage Wind's "Beta 1 fixes" (2ae4b39: lock-on and menu bindings, the ultrawide map, compute shaders
  reading copies of their constant buffers, the "Magnesis: pull closer" row, a crashed compile retried) merged.
- **BetterVR 1.0.2:** on a horse with nothing in hand the right trigger soothes it (L) instead of drawing a weapon
  (I08; `test_vr_gestures` 162 checks). Its other two changes are not needed here: the rune targets' flicker is a
  Cemu FPS++ patch, and the hair / headgear seen looking up cannot happen with the head hidden by its bones. Its
  material flags (view option bit 4, the selectable Z pre-pass) are the lead for B08, the head's shadow.
- **The PC Maker** (another agent's branch, 098e8ba) merged, with two fixes: under SAVAGEWIND_HIDDEN no error dialog
  holds a test run open (the runtime's and the AppImage launcher's), and the launcher passes TERM / INT / HUP on to
  the game and keeps the terminal's stdin (checked with a stand-in runtime).
- **The VR options in every language:** the 119 texts of Options > VR and its controls guide translated into the 12
  other menu languages; `tools/i18n_check.py` passes again (the Tests workflow had failed on main since 2026-11-21).
- **Release:** `vr-release.yml` also builds the Windows zip (make dist VR=1 on a Windows runner) and runs the x86_64
  AppImage from its FUSE mount before attaching it. Its first builds found three packaging bugs, all fixed: the
  OpenXR loader's libjsoncpp was never bundled (vr-2026.11.21 needs the system's), the Steam Frame AppImage carried
  an x86-64 loader, and the new launcher replaced the AppImage runtime's keepalive fd 3 (the AppImage unmounted
  under the game). The published x86_64 AppImage passes the 16 VR scenarios (82 checks).
- **Tests (Linux, RTX 3090, fake_xr):** every unit test (VR, Maker, bindings); `test_vr_game.py` 16 scenarios on the
  new build (two checks that failed while another game ran on the same GPU pass alone). The published
  vr-2026.11.21 AppImage passes the same 16 scenarios (83 checks) run through its own data folder.

## 2026-11-21 (the feature table as the control list; English and Spanish docs; the Linux build)

- [FEATURES.md](FEATURES.md) / [FEATURES.es.md](FEATURES.es.md) are generated from [features.py](features.py): each
  feature has three checks, implemented, validated by the AI's automated tests, validated by a human in a headset.
  The human column comes only from the player's reports.
- The docs are in English by default with Spanish next to them (`*.es.md`); the outdated ones were brought up to date
  (README, setup, the plan, the gap list, the checklist, now a short "how to test and report").
- Linux: `tools/linux/package.sh` builds the AppImage with VR (`make appimage VR=1`): the OpenXR loader bundled, it
  starts in VR. `.github/workflows/vr-release.yml` builds it and attaches it to a release.

## 2026-11-21 (BetterVR parity, first batch)

- **Throwing by hand:** the grab-throw action's throw (main+0xc76d60, called by its calc_ main+0xc76f54 at the
  animation's throw frame; vtable 0x1cd4e20, found through its ThrowSpeedF / ThrowSpeedY / SquatThrowSpeedF
  parameters) builds the velocity at sp + 4. The new patch site `grab_throw` (0xc76e20) hands it to `vr_grab_throw`:
  with the right trigger let go during a swing, the hand's velocity goes there (its fastest of the last 0.1 s, in the
  world, at most 1.2x the game's). "Carrying" is bit 17 of player + 0xc40 (set by the lift action, main+0xc7721c,
  animation GrabUp; cleared by the throw). Generated and built (233 sites); not run in the game: the test save has
  nothing to lift (`tools/vr/test_vr_throw.py` is ready for a save that does).
- **What you carry, in the hand(s):** in first person the model over his head is drawn at the right hand (small
  things, BetterVR's list) or between the hands, scaled down. Same test limit.
- **The bow's string** follows the drawing hand: the bow's String_L_2 / String_R_2 bones (5 and 9 on
  Weapon_Bow_001). `test_vr_bow` passes; in the eye's capture the string runs from the bow's tip to the hand.
- **No head shake:** Y or ZR with no weapon / bow on Link (the models vr_skel.c sees in his hands and on his back) are
  kept from the game.
- **Options:** comfort presets, stick dead zone (`test_vr_input_map`: 61), the controller rotation fix (BetterVR's,
  for the Oculus runtime), the body slots' guide (with Always, fake_xr gets 5 more discs a frame), the bow arc's modes,
  a Controls guide page. Steam Frame, Pico and Vive Cosmos bindings.
- **Climbing:** the eye sat ahead of Link's head, inside the rock; it now goes 0.3 m behind his head. Climbing the
  Plateau's big rock in the simulator (flags 0x90): `climb_eye` 0.96, the wall seen from outside.

## 2026-11-21 (whistle with both triggers; options that do nothing in VR)

- **Whistle:** both hands within 28 cm of the mouth and both triggers held. With both hands there the triggers do
  nothing else.
- **Options:** the Video rows that do nothing in VR are hidden; new Options > VR > Eye resolution (1080 to 2160, from
  the next start). Checked: it starts in VR and gets past the splash (the start crash fix, with VR really on).

## 2026-11-20 (parry with the trigger, bow and arrow menus, the arrow on the bow, slow events)

- **Slow events:** the event pacing check (`event_at_30`, framepace.c) read an environment variable on every draw
  during events (18.8 ms a frame). Read once now: the new game's wake-up went from 88 to 260-318 fps (fake_xr).
- Left trigger: guard and, at the press, a parry; A while guarding does nothing; B held no longer runs.
- Right grip held: the bows' menu; left grip held with the bow out: the arrows' menu; no arrow on letting go.
- The nocked arrow laid on the line between the hands (66° off before, 0° now in fake_xr).

## 2026-11-20 (Quest layout; the new item window; options in the game)

- The Quest layout became the default (A accept, B cancel, right stick up jump, triggers the hands' items, grips the
  bow / grab, Y rune, X map, menu pause). `SAVAGEWIND_VR_CONTROLS=bettervr` keeps BetterVR's.
- The new item window: not reproducible here; the log now says why an event goes to the virtual screen.

## 2026-11-20 (L3 to run, events at 30 fps, the bow, Quest icons)

- L3 held runs; the scope moved to R3 held. The virtual screen in stereo runs two game frames per headset frame
  (events shown flat went from 45 to 87-110 fps).
- A bow taken out by the gesture stays the bow while nothing else shows in the hands (the trigger had drawn the
  sword). Each right trigger press is logged.
- The game's button prompts drawn as the Quest controller's buttons.

## 2026-11-20 (Magnesis by hand, parry sensitivity)

- Magnesis follows the hand's travel since the grab (0.6 m sideways: a radian round Link; up: as high as it is far),
  the stick only near / far, the game camera's turns kept from the view. Checked in the simulator.
- Parry: a push of 10 cm in 0.2 s at 1 m/s (was never firing at 18 cm / 0.15 s / 1.6 m/s; before that, too eager).

## 2026-11-20 (lock-on turned the view 180°, Magnesis did not grab, things shaking)

- In first person the game camera's own fast turns (lock-on recentre) are kept from the view.
- Runes are aimed with the reticle (the head): Magnesis takes its target along the picture's centre and Link's hand.
- The stereo pair's game time split evenly (95/5 kicked physics constraints: chains and stacks shook).

## 2026-11-20 (flickering shadows in the left eye, attacks and crouching on their own)

- The right eye reusing the left one's shadow maps made the left flicker: off by default.
- An attack now also needs the hand to really travel (2 m/s slash, 1.5 m/s stab) and a melee weapon in hand.
- The eye follows Link's head only while crouched, swimming or riding (an attack's head dip looked like crouching).

## 2026-11-20 (Link did not turn with the view; the stick back walked forward)

- In stereo the right frame got 0.001 of a console frame: Link did not turn to the stick and things drifted. Fixed in
  vr_pair.h (later made 50/50).

## 2026-11-20 (Quest buttons in menus; Link walking on his own)

- In menus the buttons are the game's letters, as BetterVR's menu bindings; no gestures there.
- Roomscale only follows Link's step toward the head and gives up when he cannot get there.

## 2026-11-20 (played in the simulator: whistle, quick menu, throwing, Magnesis, swimming, gliding, riding)

- Swimming (flags 0x410), gliding (0x8002) and riding (0x100000) confirmed on the Switch game. Tools:
  `tools/vr/play_misc.py`, `play_magnesis.py`, `play_water.py`, `play_horse.py`.
- Review of another AI's (Codex) changes: correct.
- The `vr` command reports each hand's pose action active / valid / tracked.

## 2026-11-19 / 20 (first headset runs: Meta Quest 3 through Virtual Desktop, RTX 3090)

- The GPU "device lost" crash fixed (an OpenXR queue lock on every submitting call); FOCUSED, 90 stereo pairs a second.
- The hand simulator (`tools/vr/handsim.py`), the hybrid mode on the real headset, the player's movement flags
  (PlayerInfo + 0x60, + 0xcec).
- Forearm twist, the elbow following the hand, Link's body turned to the view, the eye following his head, the scope
  on the virtual screen, no depth of field or lens flare in VR.
