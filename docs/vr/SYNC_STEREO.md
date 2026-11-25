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

Speed: replaying the lists for the right eye still translates every draw twice, so synchronous stereo by itself is
not faster than normal stereo; multiview is ([PERFORMANCE.md](PERFORMANCE.md)). What it found (the camera's rows, the
passes that depend on the eye) is what multiview needs.

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
2. **The replay** (prototype, `SAVAGEWIND_VR_SYNC=1`): simpler than twins. Every game frame is a pair's left frame
   with the whole step (vr_camera.c: vr_pair always on the left eye; the right eye's camera and field made in the same
   update, `vr_sync_frame`, and queued after the left at the present). The translating thread copies each list as it
   runs it (exec.c `sync_flat`: the game records over a list's memory once the GPU is past its fence, which came during
   the right pass - a crash on the first try), and at the present, once the left eye is in its swapchain, runs the
   frame's lists again and presents that as the right eye (device.c `backend_present`, exec.c `vk_sync_replay`): the
   same targets drawn over, no twins. Left out of the second run: copies into the game's memory and its counters.
3. **The camera patch** (prototype, vr_sync.c `vr_sync_patch`): in the right pass every constant buffer is searched
   for the left eye's view (made from eye/at/up as sead::LookAtCamera does: within 1e-4 of the game's,
   `SAVAGEWIND_VR_SYNC_CHECK=1`), its inverse and the eye's place; the view-projection and projection after a view get
   the right eye's (its field's scale and centre: the projection's offset per unit of centre measured from the left
   one, 1.00). The game's camera stays the left eye's (culled with its field).

   **First result** (2026-11-25, fake_xr, Plateau, head turned 37 degrees): the right eye's picture comes from the same
   game frame, moved as an eye should be (the church, the tree, Link's arm); ~1.7 million constant buffers patched in
   4 s. But both eyes' light is wrong: the right eye has a black tree and black streaks on the grass, the left eye
   lost the grass's shadows and looks washed out. The second run redraws passes that keep state from frame to frame
   or do not depend on the eye (the shadow cascades, the exposure, histories), so the next left frame reads what the
   right pass left. Headset 103 -> 87 fps (the translating thread does everything twice, plus the copies and the
   search; the GPU 70 -> 57%).
4. **The rest**, one by one, against captures of both eyes (BetterVR's list): shadows from view space, the eye
   position, sky and clouds, reflections, particles, lights, TAA's history per eye (its previous-frame matrices).
5. **Mono passes** (done, `SAVAGEWIND_VR_SYNC_MONO=0`: everything redrawn): the left pass marks every target drawn
   by a draw whose shader reads the rows of a constant buffer that hold the camera (its view or inverse; which vec4s a
   shader reads the translator already knows, `cbuf_rows`), or that samples a texture marked before it this frame;
   copies carry the mark. The right pass runs only the draws, clears and copies into marked targets; compute is kept
   from the left (72 shaders: skinning, particles, culling, written to the game's memory). One more rule: a texture a
   marked draw read and that is written again later in the frame is marked too - the shadow map (896x896) is drawn one
   cascade after another, each read in between, and left to the left pass the right one found only the last cascade:
   the whole right eye in shadow, black but for the sky. With it the right pass redraws ~98% of the draws (the shadow
   cascades included); without it ~69%.

   Result (fake_xr, Plateau): the left eye is as in normal stereo (the same mean brightness, 162 / 162 / 160 for
   stereo, sync without the right pass, sync), the hands 0.56 m away in both modes and the far patch 4 px, as normal
   stereo. Left in the right eye: the sun's shadows wrong over a large region with a straight edge (a cascade's
   boundary: the shadow pass's matrix from view space, S * V^-1, is the left eye's - step 4, BetterVR's
   updateShadows.cpp), and one far tree black. The marks search the camera of the last 16 frames: after a stall the
   game can be several frames ahead of the translator, and with 4 the right eye came out black now and then. Headset
   85-87 fps against 102 in normal stereo: the right pass still redraws most draws, and the copies of the lists
   (~6% of the translating thread), the search for the camera (~5%) and the marks (~1.4%) come on top; simulating
   once a pair does not help while the translating thread is the limit.

6. **The context block's other rows** (done): the shadow pass's shaders (the three that sample the 896x896 shadow
   map, `SAVAGEWIND_VR_SYNC_DUMP=896` dumps their constants and GLSL) rebuild the view-space position from the depth
   with the projection's rows 7-8, pick a cascade by its depth against row 58, and read the cascade's matrix at row
   42 + 4 x cascade: three 4x4 from view space (S V^-1) at rows 42-45, 46-49, 50-53. Rows 21-34 are the last frame's
   view, view-projection, projection and inverse (BetterVR's slots 11-14). In a context block (its view, view-projection,
   projection and inverse all where they should be) the right pass puts the cascades into the right eye's view space
   (M D^-1, D = V_R V_L^-1) and the last frame's camera into the right eye's (D V, its projection, the inverse D^-1);
   about 1600 such blocks in 4 s (the shadow pass's).

   Result (fake_xr, Plateau, head turned 37 degrees): with SMAA the right eye is like normal stereo's but for one black
   far tree; the shadows are right. One shot in about six still has a darker right eye (the sky too); with
   `SAVAGEWIND_VR_SYNC_MONO=0` the black streaks on the grass come back, so the mono passes help.

## Next

- The shot in six with a dark right eye (the sky too: the exposure, or a frame the marks missed).
- The right pass without the shadow cascades: a copy of a texture that is written again after a marked draw read it
  (a version per write), read by the right pass in its place, instead of redrawing the cascades (~30% of the draws).
- The far trees, the rest of BetterVR's list (sky and clouds, reflections, particles, lights), TAA's previous-frame
  matrices per eye, and the lists kept alive instead of copied.
