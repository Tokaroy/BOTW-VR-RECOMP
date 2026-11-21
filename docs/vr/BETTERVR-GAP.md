# BOTW VR vs BetterVR: what is still missing

*En español: [BETTERVR-GAP.es.md](BETTERVR-GAP.es.md)*

BetterVR ([Crementif/BotW-BetterVR](https://github.com/Crementif/BotW-BetterVR), version 1.0.1 and the commits after
it) is the reference this mod follows: a VR mod for the Wii U version of the game, running in Cemu. This mod ports
its ideas to the Switch 1.9.0 game recompiled natively by Savage Wind.

Every feature, BetterVR's included, with its state and how far it is tested, is in the feature table:
[FEATURES.md](FEATURES.md) (the rows from BetterVR say BVR). This page lists only what BetterVR does that this mod
does not yet, as of 2026-11-21, with what each one needs. "Game code" means 1.9.0 functions or fields still to be
found; BetterVR's Wii U addresses only say what to look for ([re-notes.md](re-notes.md) has how the others were found).

| Table ID | What BetterVR does | Needs |
|---|---|---|
| U08 | **Magnesis spin**: twisting the wrist turns the held object (magnesis.cpp `hook_GetMagnesisHeldBodySpin`: an angular velocity on its rigid body right after the game pushes it) | game code: where the Magnesis manager (its instance at main+0x1e15f18) pushes the held body, and `RigidBody::setAngularVelocity` / `getTransform` |
| C34 | **Ladders**: up and down whatever the view, no getting stuck behind them (player.cpp `hook_FixLadder`, `hook_StoreLadderState`) | game code: the ladder state and the climb direction |
| K09 | **Full roomscale**: Link's body warped to where the player walks, with its own casts against the world (roomscale.cpp) | game code: the player's position update and a ray / shape cast; here the walk stick is pushed toward the head instead |
| P14 | **Third-person camera collision** skipped where it gets in the way (camera.cpp `hook_SkipCameraCollision`) | game code: the camera's collision step; here only the distance is done |
| P15 | **The sand seal camera** (game_state.cpp `hook_PlayerIsRidingSandSeal`) | game code: the sand seal riding state |
| H10 | **Screen markers on the floating HUD**: names and markers placed where the line from the eyes crosses the HUD panel (interface_hooks.cpp `hook_PlaceScreenMarker`) | game code: the camera-to-screen projection the markers use |
| H11 | **The stamina wheel** placed for the HUD panel (`hook_FixStaminaGaugeScreenPosition`) | game code: the gauge's screen position (the UI layout patches in tools/patches.py may reach it) |
| B08 | **Link's head keeps its shadow** while hidden in first person (head_visibility.cpp: the head's materials left out of the main view only) | game code: the gsys model unit's material view flags on the Switch |
| O07 | **Foveated rendering** (in its Cemu fork's shading) | the Vulkan backend: variable rate shading, or a runtime offering `XR_FB_foveation` (Virtual Desktop's VDXR did not) |
| O08 | **Recording / spectator view** (Punch In, Wider, Wider without HUD) | a separate, wider camera for the monitor window |
| G14 | **The guard's direction** set from the view (camera.cpp `hook_OverrideGuardDirection`) | probably not needed: here the game reads the view it draws, so guarding faces the view; to check in a headset |

Done since the first version of this list (2026-11-21): throwing a lifted object with the hand's velocity, the
carried object in the hands, the bow's string to the hand, no "nothing to draw" head shake, comfort presets, the stick
dead zone and the controller rotation fix, the controls guide, the body slots' guide, the bow arc's modes, the
climbing camera, and the Steam Frame, Pico and Vive Cosmos bindings.

## Where this mod goes beyond BetterVR

- **Native, no emulator.** The Switch 1.9.0 game recompiled to x86-64: about 110 stereo pairs a second at 1080 lines an
  eye on an RTX 3090 (fake_xr), so 90 Hz holds where Cemu struggles.
- **Savage Wind's PC features**: DLSS, FSR, XeSS, render scale, draw distance, shadows, and per-eye TAA in stereo.
- **The 1.9.0 game with both DLC.**
- **Linux** builds (an AppImage) next to Windows.
- **A test harness with no headset**: the fake_xr runtime, the hand simulator and the gameplay tests.
