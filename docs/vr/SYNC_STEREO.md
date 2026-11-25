# Synchronous stereo: both eyes from one game frame (in progress)

Today (`SAVAGEWIND_VR_STEREO=1`) each eye is a whole game frame: the game simulates and draws the left eye, then
simulates half a step more and draws the right eye. Whatever moves in the world (Link included) is half a step apart
between the eyes (5.6 ms of game time at 90 pairs a second; ~2.8 cm for Link running), and the game simulates twice
per pair. Giving the right frame no game time breaks the game (2026-11-25, [DEVLOG.es.md](DEVLOG.es.md)).

The goal, as [BetterVR](https://github.com/Crementif/BotW-BetterVR) 1.0.1 does it on the Wii U: **one game frame per
pair, its draws translated once for each eye**, the right eye's with its own camera. Ideas and code are taken from
BetterVR (credited in the README); its pieces and what they become here:

| BetterVR (Wii U, its Cemu fork) | Here (runtime/nvn/vulkan/exec.c, runtime/vr) |
|---|---|
| `IT_HLE_VIEW_SCOPE`: draws inside a stereo scope drawn again for the right view (LatteView.cpp) | the translating thread runs a frame's command lists (CmdRec, kept in host memory) twice: left, then right |
| right-view "siblings" of render targets: the right view writes its own copy, reads the left's until it has written its own (`LatteView_GetOrCreateSibling`) | the same: a twin texture per render target written in the right pass; textures sampled in the right pass read the twin when it was written this frame |
| mono sections: drawn once (`gpuWriteMonoSection`) | passes that do not depend on the eye (the sun's shadow cascades - world space, fitted to the game's camera, valid for both eyes -, cube maps, compute) run once |
| the camera's uniforms written again for the right view (`updateRegisterUniforms.cpp`: by caller and by content; `IT_HLE_VIEW_ALU_CONST`, `IT_HLE_VIEW_MEM_WRITE`) | the constant buffers each draw reads are copied anyway (exec.c `cbuf_info`): in the right pass the camera's matrices in them are replaced by the right eye's, found by content (step 1 below) |
| GpuView slots 0-3 (view, viewProj, proj, invView), previous-frame slots 11-14 per eye (`updateUniforms.cpp`) | cbuf 3 of the scene's shaders: view +0x00, viewProj +0x30, proj +0x70, invView +0xb0 |
| env block: the inverse view, the view 0x30 later (`updateEnvUniforms.cpp`) | cbuf 4 / 5: invView +0x2b0, view +0x2e0 |
| shadow cascades from view space (`updateShadows.cpp`), sky and clouds (`updateUniforms.cpp`), water reflections (`updateReflections.cpp`), particles and stars (`updateParticles.cpp`), lights in view space (`updateLightUniforms.cpp`) | to be found: most of them are not the camera's matrices themselves (products, view-space positions), so content search does not find them; each needs its own rule |
| culling with both eyes' frustum (`hook_getStereoProjection`) | the game's camera in the head's centre with both fields together (today's mono mode), each eye's projection put in by the patch |

## Steps

1. **Census** (done, `SAVAGEWIND_VR_SYNC_CENSUS=1`, runtime/vr/vr_sync.c): where the camera's matrices are in the
   constant buffers. Plateau, head turned 37 degrees (axis-aligned cameras - the cube map's faces - are left out, they
   match every identity matrix), 1600x900 scene, 3 windows of 30 ms: 824 places, 87 shaders.
   - cbuf 3 of the vertex stage (72 shaders, 4 more in the fragment stage): view at +0x00 (3x4, row-major as
     sead::Matrix34f), view-projection at +0x30 (its last row minus the view's third row), the inverse view at +0xb0
     (the view's columns as rows). The projection, by its place, at +0x70 (not searchable: no camera rows in it).
   - cbuf 4 / 5 (15 + 7 shaders, also in an 896x896 pass): inverse view at +0x2b0, view at +0x2e0.
   - The eye's position: cbuf 6 +0x00, cbuf 4 +0x10..+0x20 (a few shaders).
   - No per-object model-view matrices: objects carry world matrices, the camera is only in those blocks. Replacing
     them moves the geometry for the right eye.
2. **The replay, unpatched**: a frame's lists translated twice into separate targets (twins), the right pass's
   output presented to the right eye. Same picture in both eyes; checks the twins, the passes left out of the second
   run (GPU writes to the game's memory, queries, uploads), and the cost.
3. **The camera patch**: cbuf 3 and cbuf 4/5 with each eye's view and projection; the game's camera at the head's
   centre with both fields (mono mode). The eyes' geometry right.
4. **The rest**, one by one, against captures of both eyes (BetterVR's list): shadows from view space, the eye
   position, sky and clouds, reflections, particles, lights, TAA's history per eye (its previous-frame matrices).
5. **Mono passes**: the passes that do not depend on the eye run once (the cost: today the right eye costs a whole
   game frame).
