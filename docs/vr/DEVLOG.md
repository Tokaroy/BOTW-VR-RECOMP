# BOTW VR: development log

*En español (with every measurement in full): [DEVLOG.es.md](DEVLOG.es.md)*

What was done, how it was tested and what is left, newest first. Settings and tests: [../VR.md](../VR.md); reverse
engineering: [re-notes.md](re-notes.md); the state of every feature: [FEATURES.md](FEATURES.md).

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
