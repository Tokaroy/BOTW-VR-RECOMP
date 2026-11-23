# Snapdragon Game Super Resolution

The Vulkan renderer offers **Snapdragon GSR** in Video > Advanced > Upscaler. This is Qualcomm's SGSR 1 spatial shader,
ported to the renderer's built-in Vulkan GLSL pipeline. It needs no Qualcomm runtime, SDK binary, or Snapdragon GPU, so
it can run on the Linux build's Vulkan devices as well as Windows Vulkan builds.

SGSR 1 renders the scene at the selected smaller resolution and applies one edge-adaptive scaling pass before the game
draws the HUD. In the VR build it uses Qualcomm's recommended `4/255` edge threshold for VR/XR; the flat build uses
`8/255`. It has no frame history, so it avoids temporal reconstruction and its latency/history behavior. AMD FSR 1
remains available as a separate spatial option (EASU plus RCAS); AMD FSR 3 remains the temporal option in the native
Linux build.

SGSR 1 expects normalized LDR colour; the renderer skips it for HDR floating-point targets. This option is **SGSR 1**, not Qualcomm's newer Adreno Neural Fusion neural SDK. The latter ships an Android ARM64 runtime
and currently targets recent Snapdragon mobile hardware; it is not a drop-in library for this desktop Linux renderer.
SGSR 2 is also temporal and needs a different history, motion, and resource integration, so this initial addition does
not claim SGSR 2 support.

The upstream fragment shader is kept at `third_party/sgsr/sgsr1_shader_mobile.frag`; the Vulkan adaptation is embedded
as `sgsr1.frag` in `runtime/nvn/vulkan/shaders.c`. Qualcomm Innovation Center's source and binary redistribution terms
are in `third_party/sgsr/LICENSE.txt` (BSD-3-Clause). Upstream source: [SnapdragonGameStudios/snapdragon-gsr](https://github.com/SnapdragonGameStudios/snapdragon-gsr).

The Linux build can validate selection, shader compilation, and render-path execution under fake_xr. Image-quality and
GPU timing comparisons still need screenshots and measurements on real Vulkan hardware; the shader alone cannot tell
whether it is visually preferable to FSR 1 on a particular GPU.
