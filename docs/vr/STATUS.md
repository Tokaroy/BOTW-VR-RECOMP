# BOTW VR: where it stands

*En español: [STATUS.es.md](STATUS.es.md)*

A short summary of what is done and what is missing, as of **2026-11-23** (release
[vr-2026.11.23](https://github.com/guideahon/BOTW-VR-RECOMP/releases/tag/vr-2026.11.23)). Every feature, with its
three checks (implemented, AI validated, validated in the headset): [FEATURES.md](FEATURES.md). What was done day by
day: [DEVLOG.md](DEVLOG.md).

**Numbers:** 177 features; 158 implemented, 131 validated by the automated tests (fake_xr, the hand simulator), 2
validated in the headset, 1 failing in the headset (I04).

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
| I04 | The new item window shows top-left and deformed | not reproducible: the test save has nothing new to pick up, and the `give` command shows no window | a capture of the monitor window and `savagewind.log` from the headset, or a save with an unopened chest |
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
