# BOTW VR: plan

*En español: [VR-PLAN.es.md](VR-PLAN.es.md)*

Goal: a PC-VR mode (OpenXR, 6DOF, stereo) in Savage Wind Recomp with native code's frame rate, porting what BetterVR
learned on Cemu. Everything behind a flag: without `VR=1` (build) and `SAVAGEWIND_VR=1` (run) the game is upstream's.

## Where it stands (2026-11-21)

The original phases are done:

| Phase | What | State |
|---|---|---|
| 0 | Build flag, OpenXR loader, pose / projection math, the fake_xr test runtime, CI | done |
| 1 | OpenXR session on the game's Vulkan device; the virtual screen | done |
| 2 | Head tracking, the headset's projection | done |
| 3 | Stereo: a game frame per eye, the clock once a pair | done |
| 4 | The HUD apart; menus on the virtual screen | done |
| 5 | VR controllers (Touch, Index, WMR, Vive, Pico, Vive Cosmos, Steam Frame, simple) | done |
| 6 | Comfort: turning, roomscale (simple), height, HUD placement, cutscene modes, vignette, presets | done |
| 7 | Link's arms by IK, his head hidden, first and third person | done |
| 8 | Motion combat, the bow by hand, Magnesis by hand, throwing by hand | done |
| 9 | Performance: per-eye frustum, per-eye TAA; shadows once a pair (off: flicker) | partly |
| 10 | Release: installer, Windows zip, Linux AppImage, Options > VR page | done |

Each feature's state, with what the automated tests and a person in a headset have checked: [vr/FEATURES.md](vr/FEATURES.md).
The development log: [vr/DEVLOG.md](vr/DEVLOG.md).

## Next

1. **Headset validation.** The player tests the table's rows (⬜ in the human column) and reports by ID
   ([vr/CHECKLIST.md](vr/CHECKLIST.md)); failures are fixed first.
2. **The rest of BetterVR** (rows ❌ in the Implemented column), each needing 1.9.0 code still to be found
   ([vr/BETTERVR-GAP.md](vr/BETTERVR-GAP.md)): Magnesis spin with the wrist, ladders, full roomscale, the third-person
   camera's collision, the sand seal camera, screen markers and the stamina wheel on the floating HUD, the head's
   shadow in first person.
3. **Rendering:** foveated rendering (a runtime that offers it, or variable rate shading in the Vulkan backend), a
   spectator view for the monitor, more passes drawn once a pair.
4. **Upstream:** the generic hooks (projection, present, frame pacing) proposed to Savage Wind.
