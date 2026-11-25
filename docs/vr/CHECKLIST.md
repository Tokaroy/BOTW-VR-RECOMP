# Testing in the headset

*En español: [CHECKLIST.es.md](CHECKLIST.es.md)*

What to test is the feature table, [FEATURES.md](FEATURES.md): every row has an ID, how to test it and three checks
(implemented, validated by the AI's automated tests, validated by a human in a headset). The human column is filled
only from what the player reports.

## How to test

1. Start the game in VR (the VR shortcut, `Savage Wind VR.exe`, or the Linux AppImage) and load a save.
2. Pick rows whose **Human validated** is ⬜ (not tested yet), or the ones changed lately (the newest entry of
   [DEVLOG.md](DEVLOG.md) names them).
3. Do what **How to test** says.

## How to report

One line per row, by its ID:

```
C07 ok
G08 fails: the horse does not come with both hands at the mouth
I04 partly: centred now, but still stretched
```

When something fails, if you can, also send:

- a capture of the game window on the monitor at that moment (it shows the left eye);
- `savagewind.log` from the game's folder (it records what the VR mode did: `[vr]` lines);
- the headset, the runtime (Virtual Desktop VDXR, SteamVR...) and its refresh rate.
- the shortest steps that reproduce it, including the expected and observed result.

To turn a report into an automated regression case, use the scripted runtime and the guidance in
[Repeatable VR regression cases](TESTING.md). A passing fake runtime test does not replace a headset check; keep the
two validation columns separate. Do not commit saves, extracted files or generated game code; if an issue needs a save,
follow the project's [contribution rules](../../CONTRIBUTING.md).

The AI then marks the row (✅ works, ❌ fails, 🟡 partly) in [features.py](features.py), fixes what failed, and the
fix goes back to ⬜ until it is tested again.

## Steam Frame standalone (ARM64)

The experimental Linux ARM64 AppImage is available in [Releases](https://github.com/guideahon/BOTW-VR-RECOMP/releases).
Please validate these rows on the device itself; AI checks and emulation do not count as headset or gameplay validation:

- **O10:** complete first-start setup, then reach gameplay using the Steam Frame controllers. If it stops, use the
  full log path shown on the error screen (normally `~/.local/share/savagewind/savagewind.log`, or under
  `$XDG_DATA_HOME/savagewind/`; `SAVAGEWIND_DATA_ROOT` changes the data folder) and note the displayed percentage.
  The bar's 82% stage is building the game code; attach
  the entire log, since the visible error can be only `1 error generated`. Include the AppImage version, SteamOS version, Vulkan
  driver, setup time and selected VR settings.
- **V08:** check whether 1440 lines per eye is readable and smooth; try 1080 if performance suffers. On Windows with a
  1920x1080 desktop and Fullscreen saved on, choose 1440 or 1800 lines per eye, restart, and confirm the `[vr]` log
  reports that size rather than 1080. Include the `[window] VR` and eye swapchain lines if it is still capped.
- **P01:** recenter while seated at your normal distance. Report if your nose, face or hat is visible; leaning forward
  should not be needed to hide it. For a controlled comparison, launch with `SAVAGEWIND_VR_EYE_FORWARD=0.22`.
- **Stereo / scale:** watch a fast-moving object while turning your head and confirm neither eye lags or shows a stale
  frame. In Options > VR compare World scale at 100% and Eye separation at 100%, then reduce Eye separation to 80% if
  nearby objects cause crossed-eye strain. Report the comfortable values and attach the log if it contains
  `[vr] skipped stereo composition`.
- **C19 / H05:** tap the VR menu button for pause, hold it for 0.6 s to open the Savage Wind overlay, then hold it
  again to close it. X should still open the map; the keyboard should not be needed.
- **S04:** compare Snapdragon GSR 1 with Off or FSR 1 at the same quality mode. Report sharpness, artifacts and
  performance in both eyes; include the headset refresh rate and resolution.

## Before reporting a crash or a black screen

- The log's first `[vr]` lines say which runtime and headset were found.
- `SAVAGEWIND_VR=0` (or the flat shortcut) tells whether it happens without VR too.
