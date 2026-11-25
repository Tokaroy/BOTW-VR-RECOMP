# BOTW VR: where it stands

*En español: [STATUS.es.md](STATUS.es.md)*

A short summary of what is done and what is missing, as of **2026-11-24** (release
[vr-2026.11.24.6](https://github.com/guideahon/BOTW-VR-RECOMP/releases/tag/vr-2026.11.24.6)). Every feature, with its
three checks (implemented, AI validated, validated in the headset): [FEATURES.md](FEATURES.md). What was done day by
day: [DEVLOG.md](DEVLOG.md).

**Numbers:** 183 features; 165 implemented, 137 validated by the automated tests (fake_xr, the hand simulator), 4
validated in the headset, none failing in the headset. I04 (the item windows) and C35 (a quick menu does not turn the
view) were fixed and validated in the headset on 2026-11-24.

## Done 2026-11-24

| ID | What | Checked how |
|---|---|---|
| I04 | Item windows (a chest's item box, a new item, the inventory's description, the hearts) at the game's size and place | memory of PauseMenuInfo flat against VR, captures; validated in the headset |
| C35 | Closing a quick menu no longer turns the view | the camera's turn kept from the view (log line); validated in the headset |
| U07 | Rune bombs thrown with the right trigger (they fell at Link's feet); a throw without a swing goes where you look | fake_xr: round and square bombs leave his hands, the throw turned to the view |
| O11 | No freezes from the monitor window: in play it is not updated | fake_xr: no 2 s stalls in 9 runs (before: half of them) |
| O12 | Lighter barriers between render passes in VR | 88.8 -> 96 headset fps; captures the same |
| O13 | The sun's shadows once a stereo pair (the frame's eye fixed: it was read a frame off) | 108 -> ~111-114; 0.07-0.16% pixels changing between frames, as without |
| O14 | The HUD layer once a stereo pair | 86.7 -> 88.8; `test_vr_game.py` hud |
| O15 | Linux: the game geometry in video memory (write watch with userfaultfd + PAGEMAP_SCAN) | 95.6 -> 107; flat 225 fps either way |

Speed, Linux only (fake_xr, RTX 3090, 1718x1800 eyes, Great Plateau, median of 3): **85 -> ~111 headset fps**
(release vr-2026.11.24.6). Details: [DEVLOG.md](DEVLOG.md).

## Performance (measured on Windows, 2026-11-25)

Ryzen 9 9950X3D, RTX 3090, fake_xr, eyes 1718x1800, dev builds, 5 interleaved runs: **Stereo 98.5 headset fps,
Multiview 147.5 (1.50x), Mono 178.6 (1.81x)**, all three still limited by the translating thread (GPU 64-69%). Options
> VR > Rendering picks the path: **Automatic** (the default: Stereo for now), Stereo, Multiview (experimental: in a headset smoke, part of the ground and an enemy's marker showed in one eye only), Mono (never automatic). Plan and numbers:
[PERFORMANCE-PLAN.md](PERFORMANCE-PLAN.md), [PERFORMANCE.md](PERFORMANCE.md).

To check in the headset (report by ID, [FEATURES.md](FEATURES.md) O18-O21): Multiview against Stereo -
frame rate, both eyes alike, smooth stick turning, the hands following the controllers while they move (the in-game
console's `vr lead` gives how far behind they are drawn, in ms); Mono's comfort and readability.

## Done 2026-11-22 / 23

| ID | What | Checked how |
|---|---|---|
| V08 | Eye resolution 1440 lines by default, applied live (no restart) | `test_vr_eye_res.py`: 1080, 2160, 1440 in play |
| V17 | Snapdragon GSR upscaler (single pass, light, for standalone headsets) | builds and runs; image quality not measured |
| V18 | Performance rows on the VR page: FPS overlay, render scale, upscaler, its mode (Dynamic), anti-aliasing | same rows as the Video pages |
| O10 | Steam Frame / any system that keeps the window smaller: the world at the eyes' resolution, the eyes fused | `test_vr_fixed_window.py` (window held at 1280x720) |
| H05 | Savage Wind's overlay: hold the menu button 0.6 s | `test_vr_overlay.py` |
| H10 | Markers on the floating HUD (names, lock-on, map pins) placed where they are | counters; not seen in a capture |
| H11 | The stamina wheel under the hearts in first person | counters; not seen in a capture |
| B10 / B01 | The arm rig: natural elbows and shoulders, forearm roll continuous and limited | `test_vr_arm_rig.py`, views from outside (`SAVAGEWIND_VR_DEBUG_CAM`) |
| C34 | Ladders: forward climbs wherever you look | `test_vr_ladder.py` (the turn's sign on flat ground) |
| P11 | Swimming: the eye just above the water | played at Zora's Domain |
| - | Longer arm reach (the eye 22 cm ahead) | `test_vr_game.py` arms |
| - | Releases for Windows, Linux PC and Steam Frame from one workflow | vr-2026.11.22.2, vr-2026.11.23 |

## Waiting for the headset

Implemented and checked in the simulator, never seen in a headset: everything above, and most of the table (the
"Human validated" column is ⬜ for 170 rows). The first to try: **B10, B01, V08, V18, H10, H11, C34, G14, O10,
K07**. Report by ID ("B10 ok", "H11 fails: ...") with `savagewind.log`.

## Missing

| ID | What | Why it is not done | Next step |
|---|---|---|---|
| - | Animals and enemies freeze a few metres away and move again only up close (headset report, 2026-11-24) | not reproduced in fake_xr (the boars and birds near the test save not in view) | a save in front of animals that freeze, VR against flat |
| - | More VR speed: the translating thread is now the limit (100%, ~1.3 us a draw; GPU ~80%) | descriptor sets, texture and vertex setup per draw are tuned already | per-draw costs (sets 1.2 ms, prep 1.1 ms a frame) |
| H10, H11 | Seen in a capture | the test save has full stamina and no markers in the world | a save further on (enemies, pins, a stamina gauge in use) |
| C34 | Checked on a real ladder | no ladder near the test save | a save or a teleport next to a ladder |
| G14 | The guard aimed by the hand | probably not needed: Link turns to the view to guard | check in the headset that hits from the side you look at are blocked |
| K07 | Simple roomscale: walking around the room moves Link | the simple version guides him with the walk stick toward the head; full roomscale is tracked separately as K09 | test walking and a wall in the headset; confirm Link follows and the view comes back if he cannot move |
| O07 | Foveated rendering | the runtime's foveation applies to what the app draws into the swapchain, and the eyes are copied there; it needs variable rate shading inside the game's own rendering | design work in the Vulkan renderer |
| O08 | Spectator view (wider, no HUD) for the monitor | not started | the HUD-less copy shown in the window |
| V15 | Depth for reprojection | off by default: Virtual Desktop lost the GPU with it | retry with the OpenXR queue lock now in place |
| P14 | Third-person camera without collision | only the distance is done | reverse engineering the camera's collision |
| P15 | The camera riding a sand seal | not done | reverse engineering |
| B08 | Link's head keeps its shadow in first person | not done | BetterVR 1.0.2's material flags are the lead |
| U08 | Magnesis: spin the object with the wrist | not done | reverse engineering Magnesis' rotation |
| K09 | Full roomscale (Link's body moved with its own collision casts) | the simple version (K07) is partial; moving the body with its own casts is still missing | reverse engineering |
| C32, I06, O06, S12 | Partly validated by the tests | need a headset or Linux / Oculus runtime runs | headset and Linux reports |

## Known test caveats

- The in-game suite (`build/vr/run_suite.sh`, 24 tests, ~55 min) has a few timing-sensitive scenarios (cinema,
  crouch, menus, `swing_hits`) that can fail once and pass on a rerun: fake_xr's captures stall the game for ~4 s.
- After a Linux build, `build/vr/fake_xr.json` points at the `.so`: regenerate it with `make VR=1 fake-xr` on Windows.
