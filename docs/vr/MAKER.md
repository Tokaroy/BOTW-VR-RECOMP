# PC Maker

The PC Maker prepares a local folder that can be copied to the device and started without compiling the game code
there. It downloads a GitHub branch, tag or commit, copies the selected user's game files into a temporary checkout,
generates and builds the matching game library, then places the runtime and game files in a new output folder.

The game files and generated game library remain on the user's PC. The Maker never uploads them. The output folder
contains personal game files and must not be committed, uploaded or shared.

## Start it

On Windows, double-click `BOTW VR PC Maker.bat`. On Linux, run `tools/vr/maker.sh` from a project checkout. You can
also start the window with `python tools/vr/maker.py`, or use the command line:

```sh
python3 tools/vr/maker.py --target linux \
    --game-files /path/to/extracted \
    --output /path/to/new-package \
    --ref main
```

The selected game folder must contain `exefs/` and `romfs/`; the Maker checks the ExeFS files, the `NSO0` signature,
and `romfs/System/Version.txt` for 1.9.0, then checks the ExeFS build ID against the supported version table before
compiling. It also copies optional `aoc1/` through `aoc8/` folders. Saves, settings, keys and unrelated files are not
copied. The output path must not already exist. Allow at least 35 GB of free space.

The source URL defaults to `https://github.com/guideahon/BOTW-VR-RECOMP.git`; choose the ref to build in the UI or
pass `--source` and `--ref`. The Maker uses a temporary clone, so it does not change the checkout it was started
from. A failed run removes that temporary work by default; `--keep-work` retains it for debugging.
Each run creates a detailed log in `~/Savage Wind VR Maker Logs/`, including validation failures before compilation.
Attach it when reporting a Maker problem.

## Targets

- **Windows x64**: build from Windows with MSYS2 UCRT64 set up by `tools/setup_windows.ps1`. Start
  `Savage Wind VR.exe`; the folder includes a VR-named runtime, the game library and the selected game files.
- **Linux x86_64**: build from Linux x86_64. The Maker compiles SDL3, FFmpeg and shaderc from the project's pinned
  sources without containers. The AppImage and its sibling `data/` folder are a single transfer package. Start the
  AppImage or `Run Savage Wind VR.sh`.
- **Steam Frame ARM64**: build from Linux x86_64 with `--target steamframe --sysroot <path>`. The sysroot must be a
  Debian-style Linux AArch64 development root (`usr/lib/aarch64-linux-gnu`) with glibc headers/libraries and
  `libopenxr_loader.so`. The cross build uses that
  sysroot and the project's pinned SDL3, FFmpeg, Vulkan headers and shaderc sources; it does not use Docker or
  Podman. Transfer the whole folder and start its AppImage. Steam Frame performance and headset-side launch still
  need testing on the device.

For x86_64, `--cpu auto` uses the build PC's CPU as the target profile. Use `--cpu v2` (SSE4.2) or `--cpu v3`
(AVX2/FMA/BMI2) when building for a different device. Pick a profile the destination CPU supports.

The maker builds only for the host operating system: Windows packages are built on Windows; Linux PC and Steam Frame
packages are built on Linux. This avoids a hidden emulator or container dependency and lets the host SDKs build SDL3
and the other native libraries.

Each package includes `BUILD-INFO.txt` with the source commit and target. Windows saves/settings stay beside the VR
launcher. Linux saves/settings go under `data/`, next to the AppImage; the AppImage detects that folder when moved as
a unit.
If the Linux AppImage does not open, `data/savagewind-launcher.log` records the startup failure. When the runtime
starts, `data/savagewind.log` has its diagnostics; the problem report includes both logs and their previous versions.
