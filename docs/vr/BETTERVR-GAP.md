# BOTW VR vs BetterVR: what is still missing

BetterVR ([Crementif/BotW-BetterVR](https://github.com/Crementif/BotW-BetterVR), version 1.0.1 and the commits after
it) is the reference this mod follows: a VR mod for the Wii U version of the game, running in a Cemu fork. This mod
ports its ideas to the Switch 1.9.0 game recompiled natively by Savage Wind. Its controls, gestures and swing analysis
are already ported.

This page lists what BetterVR does that this mod does not, or does only partly, as of 2026-11-20. It was made by
reading BetterVR's source (`src/`, `resources/`) against this repository's [VR.md](../VR.md). Nothing here has been
checked in a headset unless it says so. The full status and settings are in [VR.md](../VR.md).

Each row says what reaching parity needs. "Game code" means 1.9.0 functions or fields that are still to be found;
BetterVR's Wii U addresses only say what to look for. "Headset" means it can only be judged while wearing one.

## Already at parity (ported)

- Stereo, 6DOF, first person with Link's head hidden, and third person.
- Arms by two-bone IK, with his armor following.
- BetterVR's controller map, body slots, quick menus, whistle, drop, throw, parry and the menu bindings.
- Motion combat: slashes and stabs (Acudofy's analysis), hits where and when the weapon is swung, one hit per swing,
  and two-handed weapons.
- The bow aimed by hand, with its arc.
- Runes aimed with the reticle (the head), as BetterVR does.
- Magnesis moved by the hand: the object hangs from the hand and the stick pushes or pulls it (2026-11-20).
- Cutscene modes, from BetterVR's table of 1497 events.
- Turning: snap, smooth and head-only. Walking by head or controller direction, simple roomscale, seated or standing,
  height offset.
- The HUD that follows the view or stays in place, and the comfort vignette.
- Rumble, the left-handed mode, the scope on the virtual screen, and no depth of field or lens flare in VR.
- The actor job-skip fix for stereo (shrine doors).
- (2026-11-21) Throwing a lifted object with the hand's velocity, the lifted object drawn in the hand(s), the bow's
  string drawn to the hand, no "nothing to draw" head shake, comfort presets, the stick dead zone and the controller
  rotation fix, the controls guide (an Options page), the body slots' guide, the bow arc's modes, and the Steam
  Frame, Pico and Vive Cosmos bindings. Checked against fake_xr where the test save allows it (docs/vr/DEVLOG.md);
  the throw and the carried object need a save with something to lift.

## Missing or partial

### Interaction

| What BetterVR does | Here | Needs |
|---|---|---|
| **Throwing by hand**: picked-up objects (rocks, bombs, pots...) fly with the hand's own throw direction and speed (player.cpp `hook_OverrideThrowDirection`, a hand throw request hooked into the game's grab-throw at the animation's throw frame) | missing: throwing is the game's R and the game's aim | game code: the grab-throw action's throw frame and the throw velocity |
| **Small objects held in one hand**: bombs, small pots, stones, Octorok grass, bottles, Cuccos, skulls and ice balls sit in the hand, scaled down for the view (their real size kept for physics), and grow back when thrown (weapon.cpp, by LiftType) | missing: Link carries them over his head as in the game | game code: the carried object's bind and the model's render scale |
| **Magnesis spin**: twisting the wrist turns the held object (magnesis.cpp `hook_GetMagnesisHeldBodySpin`, an angular velocity on its rigid body) | missing: the object follows the hand's position and aim only | game code: the held body's rigid body after the game pushes it |
| **Bow string and arrow**: the string is posed to the drawing hand, the arrow sits in it nock first, the draw can go past the animation's (bow.cpp `hook_PoseBowString`, nock geometry) | partial: the arrow flies from hand to hand and the arc is drawn; the string and arrow are the game's animation | game code: the bow model's string bones and the nocked arrow's matrix |
| **No "nothing to draw" head shake**: Y or ZR with nothing on the back does not play the shake or put the rune away (weapon.cpp) | missing | the player's equip state string; a filter on the gestures' Y and ZR |
| **Ladders**: special handling while Link is on a ladder (player.cpp) | missing (climbing walls is handled) | game code: the ladder state |
| **Prevent ragdolling** option: Link never falls over in first person (blocks the large, medium and small damage states) | not done; the view is always upright here, so it may not be needed | a headset to judge it; game code is known (re-notes) |
| **The shield's aim**: the guard faces where the shield hand points (camera.cpp `hook_OverrideGuardDirection`, after 1.0.1) | missing | game code: the guard direction |

### Camera and comfort

| What BetterVR does | Here | Needs |
|---|---|---|
| **Full roomscale**: Link's body is warped to where the player walks, with its own raycasts against the world (roomscale.cpp) | partial: the walk stick is pushed toward the head and the game walks him | game code: the player's position update and a raycast |
| **Climbing and swimming camera**: the eye kept off the wall while climbing and pinned above the water while swimming (camera.cpp `hook_CaptureClimbWallSurface`) | partial: the eye follows his head bone while crouched, swimming or riding | headset; game code for the wall's surface |
| **Third-person camera**: its distance, with the game's camera collision skipped where needed (camera.cpp) | partial: the distance only (`SAVAGEWIND_VR_THIRD_DISTANCE`) | game code: camera collision |
| **Snap turn about Link**: the game camera's pivot turned so a snap turn is about him (camera.cpp `hook_SnapTurnCameraPivot`) | done differently: the turn is applied on top of the game camera; check in a headset | headset |
| **Comfort presets** (Gentle, Balanced, Immersive) | missing: each comfort option is set on its own | nothing from the game: Options rows |
| **Stick deadzone** and **Fix controller rotation** (for runtimes with broken angular velocity) | missing | nothing from the game |
| **Hold to run while jumping and turning** (a run button besides the long A) | missing | nothing from the game: a gesture row |

### HUD and menus

| What BetterVR does | Here | Needs |
|---|---|---|
| **Screen markers on the HUD panel**: name labels and markers placed where the line from the eyes to their spot crosses the floating HUD (interface_hooks.cpp `hook_PlaceScreenMarker`) | missing: they sit where the game puts them on a flat screen | game code: the projection's camera-to-screen function |
| **Stamina gauge position** fixed for the HUD panel | missing | game code |
| **UI blending fixes** (black backgrounds and transparency glitches) | not checked here | headset |
| **An in-VR menu** (hold X): every VR setting, the controls guide and credits, usable in the headset | partial: the settings are on the game's Options > VR page (in the headset on the virtual screen); there is no in-VR controls guide | an overlay layer, or a guide image page |
| **A 3D body-slot guide** (tap X): where the bow, weapon and runes sit on the body, and a height measurement | missing | nothing from the game: a layer drawn at the slots |
| **Keep Link's head in his shadow** while it is hidden in first person (head_visibility.cpp) | missing: the hidden head has no shadow | the model's render view option (shadow) |

### Rendering and performance

| What BetterVR does | Here | Needs |
|---|---|---|
| **Foveated rendering** (in its Cemu fork's shading) | missing | the Vulkan backend (variable rate shading or a foveated pass) |
| **VR resolution multiplier** | covered by `SAVAGEWIND_VR_HEIGHT` and Video > Render scale | - |
| **Recording / spectator view** (Punch In, Wider, Wider without HUD) for trailers and streaming | missing: the desktop window shows the left eye | a separate wider camera for the window |
| **FPS overlay** in the headset | missing (only the log and the `vr` command) | a layer |
| **Depth for reprojection** | implemented but off: a Quest 3 via Virtual Desktop lost the device with it | headset |

### Platform and controllers

| What BetterVR does | Here | Needs |
|---|---|---|
| **Steam Frame controllers** bindings | missing (Touch, Index, WMR, Vive and simple controller are bound) | an interaction profile |
| **Linux** (SteamVR, WiVRn, Monado) | not tested: VR is built and tried on Windows | a Linux build with `VR=1` and a runtime |
| **Update check** banner | covered by Savage Wind's own updater for upstream; this fork has no auto-update of its own | releases |

## Where this mod goes beyond BetterVR

- **Native, no emulator.** The Switch 1.9.0 game is recompiled to x86-64, so it runs at a much higher frame rate than
  Cemu: about 110 stereo pairs a second at 1080 lines an eye on an RTX 3090 (fake_xr).
- **Savage Wind's PC features**: DLSS, FSR, render scale, draw distance, shadows, HDR, and the mod's per-eye TAA
  history in stereo.
- **The DLC and the 1.9.0 game.**
- **A test harness** with no headset: the `fake_xr` runtime, the hand simulator and the gameplay tests.

## Still to check in a headset

This list is about features. Nearly everything above "Already at parity" was verified only against `fake_xr` and the
hand simulator: see [CHECKLIST.md](CHECKLIST.md) for what to check while wearing a headset.
