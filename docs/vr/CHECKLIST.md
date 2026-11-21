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

The AI then marks the row (✅ works, ❌ fails, 🟡 partly) in [features.py](features.py), fixes what failed, and the
fix goes back to ⬜ until it is tested again.

## Before reporting a crash or a black screen

- The log's first `[vr]` lines say which runtime and headset were found.
- `SAVAGEWIND_VR=0` (or the flat shortcut) tells whether it happens without VR too.
