// Magnesis moved by the hand (BetterVR's DriveMagnesisAimFromController, src/game/botw/player/magnesis.cpp): while
// Magnesis holds something, the held object follows the main hand's moves since the grab, scaled up by its distance:
// the hand raised or lowered raises or lowers it, moved to a side swings it round Link that way - and the right stick
// only brings it nearer or sends it away. (BetterVR hangs it on a stick turned by the wrist; in a Quest 3, 2026-11-20,
// that went left and right far too readily and hardly up or down. Then the arm's direction from the chest: with the
// hand near the body the angles were lopsided the same way. The hand's own travel, smoothed, reads both ways alike.)
//
// The game's Magnesis action (1.9.0: the AI action whose vtable is main+0x1bd3b00; its loadParams_ main+0x5e87a8 reads
// MaxMagneForceRange, MinMagneForceRange ... CancelHeightFixed into +0x20 .. +0x98, pointers to the values; its calc_
// main+0x5e74b4 runs each frame while something is held). Found with the scratch save, the sword dropped on the plateau
// and Magnesis taken to it (fnprof on the vtable's functions, then mem path from the player), 2026-11-20:
//   player + 0x4e0, then + 0x180, then + 0x238: the action, while something is held (null otherwise)
//   + 0x20 / + 0x28 MaxMagneForceRange / MinMagneForceRange (pointers to floats), + 0x78 MaxMagneHeight
//   + 0xd0 the point the object is pulled to (the game's result: Link + direction x distance, + the height)
//   + 0xe8 Link's position (vec3), + 0x108 the distance (flat), + 0x10c the height (over Link), + 0x110 a yaw added to
//   the direction by the right stick, + 0x148 the direction (vec3, flat) - BetterVR's PlayerPos 0x80, Distance 0xA0,
//   Height 0xA4, Yaw 0xA8 and BaseDirection 0xC4 on the Wii U
// The game adds the sticks to the distance, height and yaw when it computes the point; they are written here before
// that (the game's input is read first in its frame) and the right stick is kept from the game while this drives.
// SAVAGEWIND_VR_MAGNESIS_HAND=0: the game's own Magnesis controls (the right stick, the d-pad).
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "../rt.h"
#include "../platform.h"
#include "../game_sites.h"

#include "vr.h"
#include "vr_math.h"

bool vr_tracking_to_world(const vr_pose *in, vr_pose *out);   // vr_camera.c
bool vr_hand_pose(int hand, vr_pose *out);                    // vr_input.c
bool vr_world_view(void);                                     // vr_camera.c

#define MAG_GUEST_OK(a) ((a) >= 0x7000000000ull && (a) < 0x7800000000ull && !((a) & 7))
#define MAG_REACH 0.6f            // m: the hand moved this far moves the object as far as it is away (up and down),
                                  // or swings it round Link by a radian (to the sides) - 10 cm about 10 degrees
#define MAG_SMOOTH 0.10f          // s: the hand's position smoothed over this (the tracking's jitter, a tremor)
#define MAG_PULL_RATE 1.2f        // the stick's length grows or shrinks by e^this a second with the stick pushed fully
#define MAG_TURN_RATE 3.0f        // rad/s: the direction the object is pulled to turns no faster (it lags behind)
#define MAG_RISE_RATE 8.0f        // m/s: the height changes no faster

static struct {
    bool on;
    uint64_t act;
    float obj_yaw, obj_height, obj_flat;   // at the grab: the object's way from Link, height over him, distance
    vr_vec3 hand0;                // at the grab: the hand from Link's feet
    vr_vec3 hand_sm;              // the hand from Link's feet, smoothed
    float scale;                  // the stick's length over the one at the grab (the right stick)
    uint64_t last_ns;
    uint32_t frames;
} m;

static uint64_t rd64(uint64_t a) { return MAG_GUEST_OK(a) ? *(const uint64_t *)(uintptr_t)a : 0; }
static float *f32(uint64_t a) { return (float *)(uintptr_t)a; }

static float param(uint64_t act, uint32_t off, float fallback) {
    uint64_t p = rd64(act + off);
    if (!p || (p & 3)) return fallback;
    float v = *f32(p);
    return isfinite(v) && v > 0 ? v : fallback;
}

// the action while Magnesis holds something (0 otherwise)
static uint64_t mag_action(void) {
    if (!g_site.player_info) return 0;
    uint64_t pinfo = *(const uint64_t *)(uintptr_t)g_site.player_info;
    uint64_t a = rd64(pinfo + 0x60);
    static const uint32_t chain[] = {0x4e0, 0x180, 0x238};
    for (int i = 0; i < 3 && a; i++) a = rd64(a + chain[i]);
    if (!a) return 0;
    // (the shape of it: a vtable in main, Link's position near the one PlayerInfo keeps, a sane distance)
    uint64_t vt = rd64(a);
    if (vt < 0x7000000000ull || (g_site.main_end && vt >= g_site.main_end)) return 0;
    const float *lp = f32(pinfo + 0x88), *ap = f32(a + 0xe8);
    float d = *f32(a + 0x108);
    if (!(fabsf(ap[0] - lp[0]) < 3 && fabsf(ap[2] - lp[2]) < 3 && isfinite(d) && d > 0.01f && d < 200)) return 0;
    return a;
}

static float wrap(float a) {
    while (a > 3.14159265f) a -= 6.2831853f;
    while (a < -3.14159265f) a += 6.2831853f;
    return a;
}

// vr_camera.c: the held object is moved by the hand now (the game's camera turning after it is kept from the view)
bool vr_magnesis_active(void) { return m.on; }

// vr_input.c, the game's thread as its input is read: drive the held object from the main hand (hand: 1 right, 0 the
// left-handed's); pull: the right stick's up-down, -1..1 (up sends it away). True while it drives - the right stick and
// the d-pad's up and down are then kept from the game.
bool vr_magnesis_drive(int hand, float pull) {
    static int enabled = -1;
    if (enabled < 0) enabled = !(getenv("SAVAGEWIND_VR_MAGNESIS_HAND") && *getenv("SAVAGEWIND_VR_MAGNESIS_HAND") == '0');
    uint64_t act = enabled && vr_world_view() ? mag_action() : 0;
    vr_pose hp, hw;
    if (!act || !vr_hand_pose(hand, &hp) || !vr_tracking_to_world(&hp, &hw)) {
        if (m.on) LOG("[vr] magnesis by hand: off (%u frames)\n", m.frames);
        m.on = false;
        return act != 0 && m.act == act;   // (the hand lost a moment: still keep the stick from the game)
    }
    uint64_t now = plat_now_ns();
    float dt = m.last_ns ? (float)(now - m.last_ns) / 1e9f : 0;
    dt = dt > 0.1f ? 0.1f : dt;
    m.last_ns = now;
    vr_vec3 player = vr_v3(f32(act + 0xe8)[0], f32(act + 0xe8)[1], f32(act + 0xe8)[2]);
    float *dist = f32(act + 0x108), *height = f32(act + 0x10c), *yaw = f32(act + 0x110), *dir = f32(act + 0x148);
    vr_vec3 rel = vr_v3_sub(hw.p, player);   // (from his feet: his walking does not move the object about him)
    float cy = cosf(*yaw), sy = sinf(*yaw);
    float have = atan2f(dir[0] * cy + dir[2] * sy, -dir[0] * sy + dir[2] * cy);   // (+0x148 turned by +0x110)
    if (!m.on || m.act != act) {
        if (!isfinite(have)) return true;
        m.obj_yaw = have, m.obj_height = *height, m.obj_flat = *dist;
        m.hand0 = m.hand_sm = rel;
        m.scale = 1;
        m.on = true, m.act = act, m.frames = 0;
        LOG("[vr] magnesis by hand: on, %.2f m out, %.2f m up\n", *dist, *height);
    }
    m.frames++;
    float k = dt > 0 ? 1 - expf(-dt / MAG_SMOOTH) : 1;
    m.hand_sm = vr_v3_add(m.hand_sm, vr_v3_scale(vr_v3_sub(rel, m.hand_sm), k));
    vr_vec3 d = vr_v3_sub(m.hand_sm, m.hand0);
    // the right stick: nearer or further (within the game's range)
    float minr = param(act, 0x28, 1.0f), maxr = param(act, 0x20, 30.0f), maxh = param(act, 0x78, 30.0f);
    if (fabsf(pull) > 0.15f) m.scale *= expf(pull * MAG_PULL_RATE * dt);
    if (m.obj_flat > 1e-3f) {
        float lo = minr * 0.9f / m.obj_flat, hi = (maxr + 1.0f) / m.obj_flat;
        m.scale = m.scale < lo ? lo : m.scale > hi ? hi : m.scale;
    }
    float flat = m.obj_flat * m.scale;
    // to the left (the grab's way turned a quarter left: x cos, z -sin) swings it left, up raises it
    float left = d.x * cosf(m.obj_yaw) - d.z * sinf(m.obj_yaw);
    float want = m.obj_yaw + left / MAG_REACH;
    float hwant = m.obj_height + d.y * (flat > 1.0f ? flat : 1.0f) / MAG_REACH;
    if (!isfinite(want) || !isfinite(hwant)) return true;
    // to the game: no faster than the object can follow (left far behind, the game lets go of it past its cancel angle)
    float step = wrap(want - have), maxs = MAG_TURN_RATE * (dt > 0 ? dt : 0.011f);
    float a = have + (step > maxs ? maxs : step < -maxs ? -maxs : step);
    float h = hwant, hmax = MAG_RISE_RATE * (dt > 0 ? dt : 0.011f);
    h = h > *height + hmax ? *height + hmax : h < *height - hmax ? *height - hmax : h;
    h = h > maxh ? maxh : h < -maxh ? -maxh : h;
    dir[0] = sinf(a), dir[1] = 0, dir[2] = cosf(a);
    *yaw = 0;
    *dist = flat < minr ? minr : flat > maxr ? maxr : flat;
    *height = h;
    if (getenv("SAVAGEWIND_VR_TRACE_MAGNESIS") && m.frames % 30 == 0)
        LOG("[vr] magnesis: hand moved %.2f left %.2f up -> %.1f deg, %.2f m out, %.2f m up\n", left, d.y,
            a * 57.3f, *dist, *height);
    return true;
}
