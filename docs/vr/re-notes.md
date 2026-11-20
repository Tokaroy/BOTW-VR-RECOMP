# VR: what the hands and the weapon in hand still need from the game

Motion combat as it is (docs/VR.md, phase 8) reads the hands and presses the game's own buttons: a slash or a stab is
the game's attack, the raised left hand its guard. What BetterVR does on top of that, on the Wii U version, needs game
functions of the 1.9.0 Switch code that are not found yet. These notes are where that stands.

## What BetterVR hooks for it (Wii U v208, its `resources/BreathOfTheWild_BetterVR/patch_CTRL_*.asm`)

| Purpose | Wii U function (BetterVR's names) | What it does there |
|---|---|---|
| Link's arms follow the controllers | `gsys::ModelUnit::getBoneLocalMatrix`, via `ksys::phys::ModelBoneAccessor` (`getBoneName`) | For the model "GameROMPlayer", each arm bone's local matrix (Clavicle, Arm_1, Arm_2, Elbow, Wrist, Wrist_Assist, Weapon _L / _R) is replaced: two-bone IK from the shoulder to the controller's grip pose |
| The weapon in the hand | `ActorWeapons::resetBaseProc`, `PlayerInfo::getActor`, `hook_SetPlayerWeaponScale` | The weapon follows the Weapon_R bone (above); its scale kept |
| The weapon's hit where it moves | `hook_EnableWeaponAttackSensor`, `ksys::phys::contactLayerFromText`, `ksys::act::hasTag` | The weapon's attack sensor (its hitbox) is turned on while the swing analysis says an attack is active, so what the blade touches is hit, scaled by the swing's power |
| Dropping, grabbing, throwing | `ActorWeapons::dropWeapon`, `PlayerOrEnemy::dropWeapon`, `requestCreateWeapon`, `CreatePlayerEquipActorMgr` | Gestures to take weapons from the back, drop and throw them |
| Roomscale and collisions | `RigidBody_getPosition / getTransform`, `SetRigidBodyPosition / Transform`, ray and shape casts | Link's body follows the player's real steps; the camera kept out of walls |

BetterVR also carries Link's skeleton (bone names, rest positions, hierarchy) as data taken from the game's model. That
can't come into this repository (AGENTS.md: no game data): it would have to be read from the player's own files at
run time, or from the model in memory.

## Link's skeleton in memory (2026-11-11)

Tools: `mem find` (text, `hex:`, `ptr:<lo>-<hi>`, `mtx:<x>,<y>,<z>,<r>` for 3x4 matrices with orthogonal rows translated
near a point) and `mem watch <addr> <len>` (the page trap of SAVAGEWIND_WATCH, armed at run time; with
SAVAGEWIND_WATCH_WRITES=<n> each write logs its host pc and the guest call chain), driven by `tools/vr/re_run.py`,
`re_bones.py`, `re_tables.py`, `re_bonewatch.py`, `re_skel.py`, `re_model.py` (each boots the game into play against
fake_xr from a scratch save).

- **Bone names in the code.** main's data has tables of sead::SafeString (vtable 0x7001bc32c8, then the text) naming
  Link's bones: 0x7001e14xxx lists the hand and arm (Finger_e2_L ... Weapon_Root_L, Weapon_L, Clavicle_R, Arm_1_R,
  Arm_2_R, Wrist_R, Finger_a1_R ... Finger_d3_R); 0x7001e45560 the clavicles, arms, legs and face controls
  (Clavicle_L / _R, Arm_1_L / _R, Leg_1_L / _R, Lash_Trans_U/V, Nose_Scale, Mouth_Scale ...); 0x7001db1xxx the horse's
  and other animals' bones.
- **Link's world matrices.** In play, 111 contiguous 3x4 matrices (stride 0x30) translated within 1.6 m of Link:
  the run `mem find mtx:` finds (one run, at the same address in runs from the same save). Next to it a second run of
  the same size 0x1500 later: the pair is a double-buffered copy (a descriptor list nearby holds both, size 0x14d0 =
  111 x 0x30).
- **Who writes them.** `mem watch` on the first matrix: one writer, a copy (guest lr 0x7000045da4) called from
  main+0xf9790c in **main+0xf978e8**, itself called through a vtable (+0x2b0) from main+0xf976cc. main+0xf978e8 takes a
  gsys model (x0), passes `x0 + 0xe0` (an embedded nn::g3d ModelObj: its first field is the ResModel, "FMDL") and its
  flags (`[x0 + 0xd8] & 3`) to main+0x41098, then tail-calls main+0x41250 with the same: the skeleton's world
  calculation and its copy out. **The hook point for the arms and the head:** before main+0xf97908 (`bl 0x41098`) the
  local matrices are animated and the world ones not yet made.
- **Found (same day):** Link's model is the one whose ResModel is named "Link" (tools/vr/re_model.py,
  re_link.py). model + 0x118 (ModelObj + 0x38) is its SkeletonObj: + 0x00 the ResSkeleton (FSKL; FSKL + 0x18 the
  ResBone array, 0x50 a bone, the name's pointer first; 121 bones, depth-first: Root, Skl_Root, Spine_1, Spine_2,
  Clavicle_L, Arm_1_L ... Neck 52, Head 53 ... Weapon_Root 120), + 0x18 the local matrices (0x60 a bone: flags, scale,
  rotation rows, translation; not read again before the skinning), + 0x20 **the world matrices** (0x40 a bone, four
  columns), + 0x50 the bone count. main+0x41098 loads ModelObj + 0x38 and jumps to main+0x45d60, which multiplies the
  world matrices by the inverse bind poses into the GPU's skinning matrices (the double-buffered run found first). So
  the world matrices at the hook (main+0xf97900) are what is drawn: runtime/vr/vr_skel.c hides the head and solves the
  arms there. The head armor and the hair's extras are models of their own ("Armor_..._Head", "Armor_Default_Extra_00 /
  01"), the arms' armor too ("Armor_..._Upper"), with the same bone names.

## Both hands on a large sword or a spear (2026-11-11): done

BetterVR (skeleton.cpp two-hand grip) latches the off hand when its grip goes down inside the weapon's bounding box, then
turns the main wrist so the blade (the weapon actor's z column) points from the main hand to the off one, and multiplies
the hits (x1.2 two-handed, x0.85 a two-handed kind held in one). Here it rides on the weapon bind site (main+0x1525fb8,
see below): after the hand's change, `two_hand` in runtime/vr/vr_skel.c turns the weapon's matrix about its origin (the
grip) so its z axis points at the other controller; the game copies that matrix to the model and the physics. The
latch zone is 0.25 m around the line (the idle animation sways a large sword's blade 10-20 cm). Checked by
tools/vr/test_vr_two_hands.py: the drawn model's blade at 0 deg from the left hand after it moved.

## Dropping what is in hand (2026-11-11): done for weapons and bows (shields: same path, not checked in the game)

BetterVR (hand over the right waist, grip held) calls Weapon::m_174_dropWeapon and ActorWeapons::resetBaseProc. On 1.9.0
the weapon's vtable (main+0x1c3f330, from its constructor main+0x7a759c) has at #175 (+0x578, one more than the Wii U for
Itanium's two destructors) a function of the same shape (main+0x7ac8bc: this, a position, two flags, a pointer, two
more flags), and the "DropWeapon" / "ForceDropWeapon" strings only lead to AI parameter tables. Calling it by hand would
still need the holder's slot reset and the pouch kept right; but the runtime already has a verified native drop of the
equipped item: upstream's quick-selector drop (runtime/quick_drop*.c: the pouch's discard plus the player's scheduled
empty equip, then waiting for the native detach; its site `quick_drop_actor_method` is the vtable's #177). So the
gesture (runtime/vr/vr_gestures.h) holds the hand's quick menu (d-pad right: weapons or bows; left: shields) and taps its drop
button (Y) 0.9 s in. The selector's cursor is still -1 then (no stick moved) in later openings: with the VR gesture on,
runtime/quick_drop.c takes the selector entry whose PouchItem is equipped (+ 0x24). Checked by tools/vr/test_vr_drop.py
(pending, completed, the sword and bow from hand height to the ground). The gesture now starts only if the skeleton
reports a melee weapon in the right hand, or a bow or shield in the left; another equipped item is not enough. BetterVR's
`isDroppable` excludes `Item_Conductor`, so the Sheikah Slate stays protected.

## The held weapon hits whenever it is swung (2026-11-11): done

BetterVR (hook_EnableWeaponAttackSensor, at Wii U 0x024AA7C4 in the weapon's attack step) writes the weapon's
`AttackSensorInitArg` (mode 2 on / 1 off, re-arm, contact layer made, power multiplier, shield break power 2) while its
swing analysis says an attack is going. On 1.9.0:

- The block: the actor of the held sword read idle and during a game attack (`press y`, tools/vr/re_attack.py): + 0xc30
  went -1 -> 2, + 0xcf8 -1 -> 2, + 0xd08 0 -> 1. The weapon's constructor (main+0x7a759c, vtable main+0x1c3f330) sets
  them up together: the set-up at + 0xc20 (mode, flags, multiplier + 0xc28, scale + 0xc2c, shield break power + 0xc30,
  override impact + 0xc34, power for players / impact + 0xc38, combo + 0xc44, contact layer made + 0xc48, re-arm
  + 0xc4c) and the sensor in use at + 0xcf4 (flags, shield break power + 0xcf8, impact + 0xcfc, scale + 0xd00,
  multiplier + 0xd04, re-armed + 0xd08, on with mode 2 + 0xd09, ...): BetterVR's two structs, 64-bit.
- The attack step is main+0x7b1670 (the only reader of + 0xc20 near + 0xd08): with + 0xc4c set and mode 0 or 2 it copies
  the set-up to the sensor in use (+ 0xd09 = mode == 2); with another mode it turns it off.
- The site: main+0x7b1690 (`ldrb w8, [x19, #0xc4c]`) -> `rt_weapon_attack` (runtime/hle/weapon.c) -> `vr_weapon_attack`
  (runtime/vr/vr_skel.c): for the actor vr_weapon_bind saw in a hand holding a melee weapon, mode 2 while vr_melee says
  a swing is going (re-armed once a swing), the multiplier BetterVR's curve of the swing's power, shield break power 2;
  mode 1 when it ends.
- Checked by tools/vr/test_vr_swing_hits.py with the game's attack press off (SAVAGEWIND_VR_SWING_ATTACK=0): + 0xd09 on in
  a fast cut, off before and after; never with SAVAGEWIND_VR_SWING_HITS=0.

## The held weapon's hits at the hand (2026-11-11): done

BetterVR rewrites the held weapon's matrix where the game binds an actor to its holder's bone (Wii U 0x0312587C ->
hook_ChangeWeaponMtx: `Weapon_L` / `Weapon_R` of "GameROMPlayer"). On 1.9.0:

- The weapon actor's matrix is actor + 0x398 (3x4 row-major), as the arrow's. Found by profiling the actor update
  main+0x1525f3c's x0 (SAVAGEWIND_FNPROF_ARGS) while the sword is out and taking the one whose matrix is at the sword
  model's root (tools/vr/re_weapon.py finds the matrices there; build-local scripts did the rest).
- `mem watch` on it: written once a frame from main+0x1525f70, `[actor + 0x4d0]->vfunc 0x20(actor)`: the bind. It asks
  the parent's model for the bone's matrix (vfunc 0x70, into the stack) and main+0x1096fb8 makes actor + 0x398 from it
  and the bind offset. Link's `Weapon_R` world matrix is read from there too (a watch on it: main+0xf96990 from
  main+0xf784d4 / 0xf77764, called by the same update, 0x15260f4).
- After the bind the update copies actor + 0x398 to the model's base (0x1526034) and gives it to the physics:
  main+0x1526180 `bl 0x12fa500(physics, actor + 0x398)`, which sets the weapon's rigid bodies (their matrices, at the
  weapon, written by main+0x12f9f7c).
- So the site is main+0x1525fb8 (right after the bind, `ldr x8, [x20, #0x4e0]`, every path goes through it):
  `tools/patches.py _weapon_bind` -> `rt_weapon_bind` (runtime/hle/weapon.c) -> `vr_weapon_bind` (runtime/vr/vr_skel.c)
  multiplies the matrix by the hand's change from the arms' turns (the one the weapon models got before) when it sits
  on a hand's `Weapon_` bone as the animation left it. Its model then comes out already at the turned hand: vr_skel.c
  counts it as held there without carrying it again. ([actor + 0x4e0] is not the gsys model vr_skel.c sees: the
  weapon is told by its place.)
- Checked by tools/vr/test_vr_weapon_hits.py (the hand 0.6 m right: the weapon's matrices 0.72 m from Link with it,
  0.42 m without).

## Magnesis aimed by the hands (2026-11-20): where the target pick goes, research in progress

What is known (fake_xr, scratch save, the sword dropped on the plateau and Magnesis aimed at it; `magx.py`-style runs:
both the head and the hand on it, or one of them 40 degrees off):

- Mono, head and hand on it: lifted. Stereo with each eye's off-centre field: nothing, whatever aimed; with the field
  made symmetric (`SAVAGEWIND_VR_ASYMMETRIC=0`, now done while a rune is aimed): the head and the hand on it lifted it,
  the hand alone did not, the head alone only with Link's arms left to the game (`SAVAGEWIND_VR_ARMS=0`; now done
  while a rune is aimed). So the GPU pick moved to the hand is not enough: something on the CPU also needs the target
  near the view's centre, and Link's (slate) hand toward it.
- **The pick's read-back** (`mem watch` on the 4x4 targets): read by a texture-decode helper main+0x1005218 /
  0x100574c (a pixel of a texture by its format into four words) from **main+0x126f21c** (x0 the pick manager, w1 the
  view's index; [x0 + 0x18] an array of 0x1a58-byte records). It reads the three targets: the first packed into
  record + 0x1968, the second and third a screen rectangle (min / max, 0..1) and the depth; it turns the depth into a
  view distance with the near / far at params + 0x680 / 0x684 (params: record + 0xbc0 + buffer x 0x6d0), and the
  rectangle's corners into world points with tan(fovy / 2) (+ 0x688), the aspect (+ 0x68c / 0x690) and the camera's
  matrix (+ 0x6a0 .. 0x6c8): the world box at record + 0x1980 .. 0x1994, its centre + 0x19a0, half size + 0x19ac,
  the view distance + 0x1998. The projection offset that makes each eye's field off-centre is not in that math (the
  reason the off-centre field took nothing).
- **The pick's set-up**: main+0x126f6a8 (called from main+0x12679a4 in the renderer's per-view step, x4 = the object
  at [renderer + 0x380]) projects through main+0x1261334 with the viewport at record + 0x19b0 .. 0x19bc into the
  screen point and hands it to the uniform setter main+0xef0f78 - the 0.5 0.5 that `rune_pick_aim` (exec.c) now
  overrides on the GPU side. The object at [renderer + 0x380] (the pick request) is where the game's own aim point
  comes from: the next step is to find who writes its point (the rune's code, with `MagnetAim2DPosOffsetY`, a Player
  parameter at param + 0xb30, registered at main+0x14e7074) and what else the rune checks (a cone about the view's
  axis?), then set that point - and the rest - from the hands.
- Magnesis' other parameters (strings in main): MagneStickMaxSearchDistance (registered main+0xa3cc5c),
  MagneStickLength (0x65843c), Max/MinMagneForceRange (0x5e87c4 ...).

## Runes aimed by the hands (2026-11-19): done, through the target pick

**Found.** The way in was the GPU, not the CPU: BetterVR's `patch_CTRL_FixScreenChecks.asm` hooks
`GX2SetPixelUniformBlock` for a 0x20-byte block and moves its first two floats (the screen point "used to test the
screen position (normally centered) for the magnesis target") onto the eye's axis. On 1.9.0 the same block is in a
draw that only aiming makes: a `dframe` (new control command: F9's debug frame, with `SAVAGEWIND_DEBUG_DATA=1` the
constants) idle and one with L held, diffed by program, gave one draw of one pixel: fs hash `30965b75b4dede22`,
viewport 1x1, three 4x4 linear targets (f0x2a, f0x2e, f0x2e), a full-screen triangle, its fragment c3 32 bytes
`0.5 0.5 0.1 25000 0.36 0.48 0.32 0.26`, reading the G-buffer (1600x900 f0x2a) and the depth. The game writes the
constants each frame (two buffers in turn, 0x...7e00 and 0x...7f00; a page watch saw 0.5 0.5 come back every frame)
and the CPU reads the targets back (no copy: the 4x4 textures are in CPU memory). The third target holds the depth at
the point (1.0 the sky).

**Done** (runtime/nvn/vulkan/exec.c `rune_pick_aim`, runtime/vr/vr_camera.c `vr_rune_aim_uv`): in that draw, in VR,
the first two floats become where the main hand's ray (grip forward, 30 m out) lands on the frame's eye picture
(`vr_ray_picture_uv`, vr_math.h; v from the top: checked, the hand up reads the sky); with
`SAVAGEWIND_VR_RUNE_AIM=head` the eye's own axis (mono: the centre; stereo: each eye's off-centre middle, BetterVR's
fix). Written as UpdateUniformBuffer would (`hc_cpu_wrote`, `uub_note`).

**Checked against fake_xr** (scratch save, Stasis, the plateau start): the head still and the right hand turned 20
degrees right and 6 up onto a Stasis candidate beside a pine (pick 0.634 0.467), the candidate took the target's
colour (yellow-green instead of the others' orange) and A froze it (Stasis' yellow lines to it, the aim ended). The
same pose with `head`: the candidate stayed orange and A did nothing (the centre was grass). So the CPU takes its
target from the pick's read-back, not from a ray of its own along the camera. `tools/vr/test_vr_rune_aim.py` keeps the
pick's part (hand ahead / up / down -> v bands, the sky's depth), mono and stereo.

Not done: the game's reticle stays at the view's centre (a 2D HUD element; the hand's ray is drawn as dots instead); Magnesis and Cryonis were not tried (same
pick, BetterVR names it the magnesis target); the shield aimed with the hand is separate.

## Runes aimed by the hands (2026-11-12): research before the pick was found

Trigger correction (2026-11-12): the right trigger was sending R while a rune was selected. The game's prompt says
“E · Paralizar”; Nintendo's [Explorer's Guide](https://zelda.nintendo.com/breath-of-the-wild/assets/pdfs/ExplorersGuide.pdf)
says L accesses the equipped rune and A activates it. In a fake_xr capture, R removed the targeting prompt and showed
the equipped weapon; this was not rune activation. `vr_gestures.h` now sends A (`VRB_A`) for the right trigger with a
rune out. `tests/vr/test_vr_gestures.c` covers this; `tools/vr/test_vr_runes.py` selects a rune with a left-waist
gesture and checks the trigger sends A (`0x1`) without R (`0x80`) or ZR (`0x200`). This checks button routing, not
hand-directed rune targeting, which remains below.

Wanted: Stasis / Magnesis / Cryonis target what the main hand points at, not the head's gaze (in first person the
gaze already aims them, which works). On 1.9.0, with the scratch save (Stasis), `press l` enters the rune's aim
(reticle, "Paralizar" prompt):

- `fnprof start` / `fnprof stop <file>` (new control command, runtime/fnprof.c) over 3 s idle and 3 s aiming: 251
  functions only while aiming. A block at main+0xb9bd78 .. 0xb9cc38 (twice a frame), next to the `MagneCatchCatch`
  xref (0xb99974), is the rune's UI and state flags (main+0xb94b10 everywhere), not the ray. Others once or a few times
  a frame: 0x12e1b58 / 0x12e1b64 (type-id checks, 25 a frame, from 0x11846f4 .. 0x11847f0: a candidate's position by
  its kind), 0xfab840 (from 0x1070968 .. 0x1070a78), 0x1546450 (from 0x10e91c0 .. 0x10e9240), 0x7903b4 (from
  0x10726f4, 0x1072178, 0x56d970), 0x12d4df0, 0xfabd40, 0x10fa004, 0x10e93c8, 0x573538 (from 0xb93048).
- The view camera (`vr` now reports `lookat_camera`, the sead::LookAtCamera rt_lookat last gave the head) is read by
  dozens of functions a frame (`mem watch` on its matrix, eye and at); the ones new while aiming were not told apart
  from that noise yet.
- `MagnetAim2DPosOffsetY` (a Magnesis parameter, main+0x14e7074 sets it up at obj + 0xb30) suggests a 2D aim point,
  but no screen-centre pair (640, 360 or 0.5, 0.5) appears or changes in memory when aiming.

Second round (`fnprof start <x> <y> <z> <r>`: also which functions get, in x0..x7, a pointer to three floats within r
of a point; `<file>.near` lists function, register, offset):
- Given the drawn eye while aiming, the only aim-only function is main+0x1546450 (an angle wrap) with x1 a ray on the
  caller's stack: the direction at +0 (the gaze pitched ~15 degrees down while aiming), the eye at +0x10. Its callers
  (main+0x10e6538, 0x10e7194 from 0x10e68a0, under the actor update 0x1525f3c -> 0x10e753c -> 0x10e5c64) are Link's
  look-at IK (bone indices at +0x138, angle limits 0.9 / 0.86): the body turning to the aim, fed with the aim ray, not
  the pick of the target.
- Given that direction (computed live from `camera`, r 0.03), no aim-only function but that helper: the ray is made by
  code that runs when not aiming too.
- Given the game's own orbit camera eye (`cell camera.eye`, which moves closer while aiming), only main+0xc32fb8 (sets
  flag 0x20 at camera + 0x800) is new: not the ray.

As with the bow before its shot was found, the aim most likely follows the camera's matrix, which is also what is
drawn; the way on is the ray's own code: the raycast the rune's target search makes (its start at the camera's eye,
the direction its forward), found among the aim-only functions above with `SAVAGEWIND_FNPROF_ARGS` (x0..x5 at entry:
a start and end Vec3 near the eye) and then overridden with the hand's ray, as `_arrow_aim` does for arrows.

Retest note (2026-11-12): `fnprof_start()` cleared its counters but did not enable `g_fnprof`, so a manual capture could
look empty. It now enables collection after resetting the filters. A 3 s idle / 4 s aim capture reported 12,976 / 13,621
functions; aim added 1,114 unique functions. Those candidates still need to be separated from unrelated frame work before
patching a target ray.

Trace safety (2026-11-12): optional `SAVAGEWIND_FNPROF_ARGS` dumps now check that each guest range is mapped before
reading register pointers or scanning a possible string, and bound the formatted line. Rune profiling previously hit an
invalid guest pointer (`0xffffffffffffffff`) and stopped the game; the guarded capture completed a full idle/aim run and
reported over 13,000 functions without an access violation. This keeps candidate searches usable; it does not locate
the target ray.

SIMD argument capture (2026-11-12): `SAVAGEWIND_FNPROF_ARGS_VEC=1` prints the four float lanes of `v0-v7` for the
selected functions. The guarded fake-XR L-aim capture completed with the option enabled. It exposed Link's body matrix
in `main+0x10e7050` / `main+0x10e7194`. The `main+0x13a4dc8` / `main+0x11848c0` proximity path receives a nearby
world-space point, but this stationary-pose capture does not distinguish camera/player geometry from a controller
target. `main+0xb7d9c` computes a geometric distance test and is entered from `main+0x15df48`; that alone does not
establish a rune target query. No hook was added; the target search remains open.

Candidate filtering (2026-11-12): main+0x165460, reached through a generic geometry helper, looked like a possible ray
query. Its two input position records were near Link's body, and its call count fell from 8,260 idle to 5,821 while
aiming, so it is not established as the rune target ray and is not hooked. Another aim-only address, 0x7002746970, first
looked unclassified because `tools/sym.py` assumed a fixed SDK base and omitted subsdk0. `tools/layout.py` gives the
actual 1.9.0 layout (main 0x7000000000, subsdk0 0x7001e98000, sdk 0x7002504000); the address resolves to
`sdk+0x242970`, `nn::audio::server::VoiceContext::UpdateStateByDspShared()`, unrelated audio work. The symbolizer now uses the same
computed load layout as the runtime, avoiding this false lead. The rune target search remains unlocated.

Proximity helper filtered (2026-11-12): main+0x11848c0 calls main+0x11846c0 to get a shape's centre, measures its distance
from the Vec3 passed in x1, subtracts a radius and clamps the result to 0..1. Its caller main+0x13a4e34 stores that scalar;
the point is passed through main+0x13a4dc8. With `SAVAGEWIND_FNPROF_ARGS` during L-aim, x1's first three floats were
(-940.35, 225.16, 1879.54). Repeating with fake_xr head yaw 30 degrees left those floats unchanged (the game reported
Link yaw 33.8 degrees), so this path did not pass the expected view-dependent point in that check. It is not established
as the rune ray and remains unhooked.

SIMD near-point filter (2026-11-12): `SAVAGEWIND_FNPROF_NEAR_VEC=1` extends the live `fnprof start <x> <y> <z> <r>`
filter to snapshot low-lane scalar HFA triples (`s0..s2` through `s5..s7`) and three-float windows in `v0..v7` at
function entry. This is an entry-register pattern scan, not proof that a function received or used those coordinates;
lifted code can overwrite SIMD registers before reading them, and dispatch stubs commonly leave matching values behind.
The guarded fake-XR idle/L-aim capture ran without a crash, but the strongest changing hits were dispatch/control-flow
functions. The one plausible SIMD consumer, `main+0x10575a4`, reads its vector registers only after loading/replacing
them in the function body, so its entry match is stale. No rune-target candidate was established and no game hook was
added. Treat these rows only as leads to check against the lifted function and caller before interpreting them.

## Indirect-call dispatch trace (2026-11-12)

`SAVAGEWIND_FNPROF_DISPATCH=<return-pc>[,...]` records selected guest indirect calls while `fnprof` is active: the
return PC in `x30`, the resolved method in `pc`, and `x0..x5`. `SAVAGEWIND_FNPROF_DISPATCH_VEC=1` adds the low four
float lanes of `v0..v7`; `_MAX` limits records per selected site (8 by default). `*` records the first `_MAX` indirect
calls overall and can be combined with selected return PCs. This runs at the shared guest dispatcher and does not patch
the game method. A scratch-save fake-XR L-aim run verified both wildcard and exact-site filters; the game exited cleanly.

The held-L run entered `main+0x1863d0` 2,725 times in five seconds. Its indirect call at `main+0x18649c` resolved
mostly to `main+0x17fc5c` and occasionally to `main+0x18901c`. The lifted caller transforms a supplied 3D vector and
calls the object at `x0+0x28` through vtable slot `+0x50`; the resolved methods perform shape/vector calculations.
Captures with the head turned 30 degrees and with the left hand turned 60 degrees produced changing inputs across
several callers, without a repeatable per-callsite change that identifies this as the rune's ray or proves hand-directed
aim. It remains a geometry lead, not a confirmed target query; no game hook was added. The rune-target search remains
open.

## Quick-selector prompt visual check (2026-11-12)

With `quick_drop=1`, the saved Spanish-language game and fake_xr, a 1030x579 selector capture shows the overlay prompts
“Tirar” and “Atrás” once each, side by side on one baseline. The “Cancelar” below “Descartar” report did not reproduce
in this capture. It confirms the fake runtime/window layer only; a Quest capture is still needed to tell whether the headset
renders an extra copy or uses a different language/layout.

## The bow aimed by the hands (2026-11-11): done

**Found.** BetterVR (src/hooking/bow.cpp) overrides two things at the shot: the arrow's launch transform and the
"FirstSpeed" / "TargetPos" parameters the bow passes to the arrow's AI. On 1.9.0 the strings are in main .rodata
("FirstSpeed" 0x163804c, "TargetPos" 0x165aa4b, "HomingTargetPos" 0x16325aa, "IsShootByPlayer" 0x161b425) and an
adrp/add xref scan gives the code that adds them to an `InlineParamPack` (`addVec3` main+0x10775f8, `addFloat`
0x1077580, `addBool` 0x107768c). The player's shot is **main+0x931364** (it runs once a shot; x19 its AI, [x19 + 8] the
arrow actor):

- It takes where the arrow is (the arrow actor's matrix translation: actor + 0x3a4 / 0x3b4 / 0x3c4) and the shooter's
  aim point (a Vec3 from main+0x7b36b4, copied to x29 - 0x50), makes the unit direction s8 s13 s9 (0x931554 ..
  0x93158c), then FirstSpeed = direction x speed (sp + 0x60) and TargetPos = the aim point, into the pack.
- Only changing the direction (FirstSpeed) does nothing: the arrow flies at its TargetPos. Both are changed:
  `tools/patches.py _arrow_aim` at 0x931590 (`mov x0, x20`, right after the direction) hands the direction, the origin
  and the aim point (at sp + 0xa90: x29 is a cached local in the lifted function, `c->x[29]` is stale there) to
  `rt_arrow_aim` (runtime/hle/arrow.c) -> `vr_arrow_aim` (runtime/vr/vr_skel.c), which, in first person and for an arrow
  within 3 m of Link, puts the direction on the line from the string hand to the bow hand and the aim point on that
  line as far away as it was.
- main+0x92ce7c is a similar shoot step (the arrow's own +0xc30 start, +0xc3c target, +0xc79 player flag) that does
  not run for the player's bow shots.
- Checked by tools/vr/test_vr_bow.py: the head looking at 33.8 deg, the hands 60 deg to the right (-26.2 deg), the
  arrow flew at -28 deg (before: 33.4 deg).

History of the search:


BetterVR (Wii U) overrides the arrow's launch transform where AI_Arrow::handleStateShoot sets the arrow's rigid body
(patch_CTRL_EntityController.asm 0x02706270 -> hook_OverrideArrowShotTransform, src/hooking/bow.cpp), and its
"TargetPos" parameter loads. On 1.9.0 so far:

- The bow and the arrow are in the hands: the weapon models at Link's hands are read (`Weapon_Bow_001` at the left,
  `Weapon_Arrow_001` at the right while drawing; runtime/vr/vr_skel.c) and follow the IK hands.
- Tried: while drawing, the LookAtCamera's eye / at set along the bow (from the string hand to the bow hand) and the
  view matrix written back with the head's at the end of doUpdateMatrix (a site at 0x7000eb2e4c, its `ret`). The arrow
  still flew where the head looked (it landed at the view's heading, 33.8 deg, with the hands aiming 60 deg to the
  right): the aim follows the camera's matrix, which is also what is drawn. Removed again.
- The matrix reaches the GPU through a generic uniform-block setter (main+0xef0f78, from main+0xf86e80; `mem find
  view:<eye>,<r>` lists the 93 copies of the view matrix and `mem watch` on them names it), at render time, from the
  same camera. Decoupling the aim from the picture there would mean telling the view's uniform apart from the rest.
- Second round: the function profiler (SAVAGEWIND_FNPROF) over a whole run shooting and one not shooting: 87
  functions run only when shooting. A block at main+0x9cd7d4 .. 0x9d7434 runs once a frame while an arrow flies (176
  frames for one shot): the arrow's AI. Of the ones run once a shot, main+0x9d50e4 reads the arrow actor's matrix
  (actor + 0x39c, 3x4 row-major; actor = [AI + 0x188]) and sets a random 5-35 s timer: it is **the arrow sticking**
  (its state when it lands), not the launch (it runs before the trigger is pulled for arrows of earlier shots, and
  long after letting go). Hooking it changed nothing; removed. The "IsShootByPlayer" users all run equally with and
  without a shot: parameter set-ups, not the shot.
- Still to find: the arrow's launch (the AI state entered when the bow is let go, among the arrow AI block's other
  once-a-shot functions: main+0x9cd7d4, 0x9ce3dc, 0x9d6780, 0x9d6be0, or the player's side: main+0x812080 .. 0x812ddc,
  0x684e5c, 0x68717c, 0x687bb0, 0xbcb250, 0xbde780, 0x138c1dc, 0x138fdbc, 0x1390898), then where it sets the arrow's
  matrix or velocity. A frame-exact window (SAVAGEWIND_FNPROF=<from>:<to> around the release, the arrow seen leaving in
  SAVAGEWIND_VR_LOG_MODELS=Weapon_Arrow) separates the launch from the flight.

## Actors' job-push skip in stereo (2026-11-19): done, to be checked in a shrine

BetterVR (`patch_RND_StereoRendering_ActorJobs.asm`, Wii U `0x037A1B3C li r12, 4`) doubles a count the game sets to 2:
"the game skips job pushes by setting this counter to 2; in stereo rendering this code is executed twice per frame
(once per eye), so this timeout is now doubled to 4 ... this fixes LinkTag and EventTag actors not updating properly
... which breaks dungeon doors and many other things". Savage Wind's stereo has the same shape (two game frames a
moment, the right one with almost no game time), so the same count runs out halfway.

Found in 1.9.0 by the shape of BetterVR's `custom_Actor_decrementSkipJobPushTimer` (a byte loaded, `cbz`, minus one,
stored back): 15 such byte counters in `.text`; the one at actor `+0x684` is in the actor code next to the update
(`0x1525f3c`) and has exactly one store of a constant:

| Address | What |
|---|---|
| `main+0x1531ffc` | `mov w8, #2; strb w8, [x0, #0x684]; ldr x0, [x0, #0x598]; cbz; b 0x10c5e74`: a virtual method in every actor's table (dozens of relocations), the count set to 2: the patched `mov` (tools/patches.py `_job_push_skip`) |
| `main+0x1527ee4` | `ldrb; cbz; sub #1; strb`: the count down, called from three actor calc paths (`0x11657a8`, `0x116ec60`, `0x1170714`), each right before `0x1515078` (with `w1`: the job push) |
| `main+0x1527ef8` | the count 0, `+0x1a0` null and a flag at `[+0x7c8]` bit 17 clear: 1 (read at `0x10bbb70`) |

`rt_job_push_skip` (runtime/hle/actor_jobs.c) returns 4 in stereo play (`vr_job_skip_doubled`, logged once), 2
otherwise; `SAVAGEWIND_VR_JOB_SKIP=0` keeps 2. Not yet seen in a shrine either way: what to try is a door opened by a
switch (a LinkTag) in stereo, with and without it.

## What is found in 1.9.0 so far

A scan of the main module (`.text`) for the shape of a 64-byte bone array accessor (index << 6, a halfword or byte flag
or'ed and stored back, a 3-float scale) gave one cluster of model bone accessors, the runtime addresses of 1.9.0
(build cd57b23fa4bbad65):

| Address | Shape | Guess |
|---|---|---|
| `0x7000f961c4` | `x0 + 0x118 -> + 0x20` bones, `idx << 6`; flag at `+8` (halfword) `| 8`; 64 bytes copied out, transposed | a bone's matrix, read for someone else (a 4x4 / 3x4 layout change) |
| `0x7000f9621c` | flag at `x0 + 0x170` (byte) `| 4`; returns `x0 + 0x198 -> + idx << 6` | a bone's local matrix, handed out to be written (marked dirty first): the closest match to BetterVR's hook point |
| `0x7000f96254` | `x0 + 0x128`, rows of 128 bytes, a 32-byte table at `+0x58`; writes up to five floats to x3 / x4 / x5 | an animation or shape parameter, not a bone matrix |

None is confirmed. Counted in play with the function profiler, no patch needed (`SAVAGEWIND_FNPROF=2500:3500`
`SAVAGEWIND_FNPROF_BT=7000f9621c,7000f961c4,7000f96254`, flat, on the Great Plateau; runtime/fnprof.c):

| Address | Calls in 1000 frames | First caller (guest lr) |
|---|---|---|
| `0x7000f9621c` | 324 | `0x700159498c` |
| `0x7000f961c4` | 18 | `0x70012f828c` |
| `0x7000f96254` | 2 | `0x70010e57d4` |

So none of them runs for every bone every frame: the arms' animation writes its local matrices another way, and the
accessor BetterVR uses on the Wii U is something else on the Switch (or is reached only by some actors). The way on:
`SAVAGEWIND_FNPROF` over a window where Link only stands, then one where he swings a weapon, and the functions whose
count goes up by about (arm bones x frames) are the candidates; `SAVAGEWIND_FNPROF_BT` then names their callers.

The next steps:

1. Log the callers of `0x7000f9621c` in play (a patch in tools/patches.py that calls the runtime with x0 and w1, the
   way `_lookat_update` calls `rt_lookat`), and find the calls whose model is Link's (the same model unit every frame,
   near Link's position from `PlayerInfo` +0x88).
2. Get the bone names from the model (nn::g3d's skeleton keeps them: a dictionary of names next to the bone array),
   and so the indices of Clavicle_R ... Weapon_R.
3. Port BetterVR's arm IK (src/hooking/skeleton.cpp) to C over runtime/vr/vr_math.h, with unit tests, and write the
   arm bones' local matrices there each frame, after the game's animation and before the matrices are used.
4. Then the weapon's attack sensor: find what turns it on in an attack animation and call it from vr_melee's
   attack state.

Each needs the game running and, for the arms, a headset to judge the result.

## The player's movement flags (2026-11-19): found

The player object (PlayerInfo + 0x60, the same object the fall-damage cells use) holds BetterVR's PlayerMoveBitFlags
at **+0xcec** on 1.9.0. Found with the hand simulator (tools/vr/handsim.py) by reading the object's first 0x3000 bytes
standing, crouched, walking and at a wall, and keeping the words that changed by a bit or two: standing 0x18000001,
crouched 0x18000005 (1 << 2), in the air after a jump 0x18000002 (1 << 1), climbing 0x00000090 (1 << 4 | 1 << 7: the
bits 27 / 28 BetterVR names event flags drop while climbing). The bits match the Wii U enum. Seen later with the
play tools: on a horse 0x100000 (1 << 20; tools/vr/play_horse.py, by the Dueling Peaks stable), swimming 0x410
(1 << 4 | 1 << 10) and gliding in the air 0x8002 (1 << 15; tools/vr/play_water.py, Zora's Domain); mounting a wild
horse that bucks reads 0x80000000 (bit 31, BetterVR's GET_HIT_MAYBE_UNABLE_TO_INTERACT). Ragdoll (1 << 19) is taken
from the enum, not seen. runtime/vr/vr_skel.c `vr_player_flags`; `vr` reports `move_flags`.
