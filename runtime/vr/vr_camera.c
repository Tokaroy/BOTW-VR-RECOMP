// VR mode, phases 2 and 3: the headset moves the game's camera, the game draws the headset's field of view, one eye a
// frame.
//
// In play (not paused, no event, no title, map or loading screen) the world's view cameras (runtime/hle/freecam.c
// rt_lookat: sead::LookAtCamera eye / at / up) take an eye's pose on top of the game's own camera: the game's camera
// keeps its position and heading (it still follows Link and turns with the stick), the head adds its turn and its
// movement since the last recentring, and gives the pitch and roll itself (a view that tilts without the head tilting
// makes people sick). The world camera's projection (runtime/nvn/output_scale.c rt_persp) becomes a symmetric frustum
// that holds the eye's field, in the window's shape (the window takes the headset's shape at start: vr.c).
//
// Stereo (phase 3): the game's frames come in pairs, left eye then right eye (SAVAGEWIND_VR_STEREO=0: one picture for
// both, phase 2). The game's clock (runtime/hle/framepace.c rt_vfr_update, vr_frame_ratio) takes both frames' time in
// the first and nearly stops in the second, as it does for the free camera: both eyes see the same moment, and the
// world keeps its speed. The headset's frame is made once a pair (xr_vulkan.c), so at 90 Hz the game runs at 180 fps.
//
// Which eye, pose and frustum a frame was drawn with travels with it: nvnQueuePresentTexture (the game's thread, at the
// end of its frame: vr_present_mark) queues it, the present on the queue thread (vr_present_take) takes it in the same
// order, and the headset is told exactly what each picture is.
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#include "../rt.h"
#include "../framepace.h"
#include "../platform.h"
#include "../game_sites.h"
#include "../control_cells.h"
#include "vr_event_table.h"
#include "vr_options.h"
#include "../settings.h"

#define XR_USE_GRAPHICS_API_VULKAN
#include <vulkan/vulkan.h>
#include <openxr/openxr.h>

#include "vr.h"
#include "vr_internal.h"
#include "vr_math.h"
#include "vr_pair.h"

#define QUEUE 32

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static struct {
    int stereo;            // -1 not read yet
    bool have_neutral;     // the head's pose at the last recentring
    vr_pose neutral;
    bool recenter;         // asked for (vr_recenter): taken at the next camera update
    float turn;            // snap turning's turns so far (radians, +: to the left), on top of the game camera's heading
    float window_aspect;   // the window image's width / height
    float out[9];          // the last eye / at / up written
    bool out_ok;
    float game[9];         // the game's own eye / at / up, as it last set them: a camera that holds still is not set
                           // again, and what rt_lookat then sees is what was written here last (so is the camera's copy)
    vr_pair pair;          // stereo: which eye each frame draws, and its game time (vr_pair.h)
    bool cam_set;          // a camera of this frame has been set, not yet presented
    vr_view cur;           // what the frame is drawn as (its cameras' last setting)
    float tan_x, tan_y;    // the frustum this frame's world camera gets
    vr_view q[QUEUE];      // frames presented by the game, not yet by the queue thread
    unsigned q_head, q_count;
    uint64_t updates;
    int first;             // -1 not read yet: SAVAGEWIND_VR_VIEW (first, the default, or third)
    float eye_height, forward;  // first person: the eye above Link's feet, and ahead of his head's centre (m)
    float eye_used;             // ... the height used last (Standing: the player's own)
    bool fp_now;           // the last camera was set in first person
    int events;            // -1 not read yet: SAVAGEWIND_VR_EVENTS (EV_*)
    bool in_event;         // the last camera was set in an event
    float event_yaw;       // the view's turn kept through a still first-person event (the one before it)
    float last_yaw;
    float off_x, off_y;    // the frustum's centre off the view's axis (tan units; 0: symmetric)
    struct {               // roomscale: Link walked under the head (vr_roomscale_stick)
        bool driving, have_lp;
        double lp[3];      // Link's position at the last camera
        float x, y;        // the walk stick it asks for (-1..1; y ahead)
        float gx, gz;      // the head from Link's eye on the ground at the last camera (m, the game's world)
        float best;        // the nearest the head got while driving, and when (plat_now_ns): a stall gives up
        uint64_t best_ns;
        uint64_t frames;   // cameras it walked him on
    } rs;
    vr_anchor anchor;      // the tracking space -> the game's world, as the last camera used it
    bool anchor_ok;
    double anchor_lp[3];   // Link's position that camera was made from (first person)
    bool anchor_lp_ok;
} c = {.stereo = -1, .window_aspect = 1, .first = -1, .events = -1};

static float env_f(const char *name, float def, float lo, float hi) {
    const char *e = getenv(name);
    float v = e ? (float)atof(e) : def;
    return v >= lo && v <= hi ? v : def;
}

// SAVAGEWIND_VR_VIEW=first (the default): the eye is in Link's head, as in BetterVR; third: on the game's own camera
// behind him. SAVAGEWIND_VR_EYE_HEIGHT (1.55 m above his feet) and SAVAGEWIND_VR_EYE_FORWARD (0.18 m ahead, out of his
// head's model) place it.
static bool first_person(void) {
    bool first = vr_opt(VR_OPT_VIEW) == 0;   // (live: the Options screen's VR page)
    if (c.first < 0 || first != c.first) {
        c.first = first;
        c.eye_height = env_f("SAVAGEWIND_VR_EYE_HEIGHT", 1.55f, 0.3f, 3.0f);
        c.forward = env_f("SAVAGEWIND_VR_EYE_FORWARD", 0.18f, 0.0f, 1.0f);
        if (c.first) LOG("[vr] first person: the eye in Link's head (%.2f m up, %.2f m ahead; SAVAGEWIND_VR_VIEW=third: "
                         "the game's camera)\n", c.eye_height, c.forward);
        else LOG("[vr] third person: the view on the game's camera (SAVAGEWIND_VR_VIEW=third)\n");
    }
    return c.first;
}


static int trace_left = -1;
static void trace(const char *what, int eye, int world) {
    if (trace_left < 0) trace_left = getenv("SAVAGEWIND_VR_TRACE") ? atoi(getenv("SAVAGEWIND_VR_TRACE")) : 0;
    if (trace_left > 0 && vr_world_view()) {
        trace_left--;
        LOG("[vr-trace] %s eye %d world %d\n", what, eye, world);
    }
}

static bool stereo_on(void) {
    if (c.stereo < 0) {
        const char *e = getenv("SAVAGEWIND_VR_STEREO");
        c.stereo = !(e && *e == '0');
        LOG("[vr] %s\n", c.stereo ? "stereo: a frame per eye, the game's clock once a pair"
                                  : "mono: one picture for both eyes (SAVAGEWIND_VR_STEREO=0)");
    }
    return c.stereo;
}

// ---- events (cutscenes): BetterVR's modes (SAVAGEWIND_VR_EVENTS) ----
//   auto    (the default) as BetterVR's table says for each event (runtime/vr/vr_event_table.h, from BetterVR's
//           patch_Settings_Cutscenes.asm): in first person or on the event's camera; unknown events on its camera
//   first   always in first person (in Link's head)
//   third   always on the event's camera, in 3D, the head free to look around
//   screen  on the virtual screen, flat (as before)
// In first person an event the table marks still (PAN_OFF) does not turn the view with its camera (the turn before it
// is kept), and one that leaves Link's hands to the animation (HND_OFF) gets no arms from the controllers.
enum { EV_AUTO, EV_FIRST, EV_THIRD, EV_SCREEN };

static int events_mode(void) {
    int m = vr_opt(VR_OPT_EVENTS);   // (live; EV_* in the option's order)
    if (m < EV_AUTO || m > EV_SCREEN) m = EV_AUTO;
    if (c.events != m) {
        c.events = m;
        static const char *const names[] = {"as BetterVR's table says", "in first person", "on the event's camera",
                                            "on the virtual screen"};
        LOG("[vr] events (cutscenes): %s (SAVAGEWIND_VR_EVENTS)\n", names[c.events]);
    }
    return c.events;
}

static const vr_event_setting *event_setting(const char *name) {
    int lo = 0, hi = (int)(sizeof vr_event_table / sizeof vr_event_table[0]) - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2, d = strcmp(name, vr_event_table[mid].name);
        if (!d) return &vr_event_table[mid];
        if (d < 0) hi = mid - 1;
        else lo = mid + 1;
    }
    return NULL;
}

// in an event now, how it is shown: fp in first person, still (its camera's turns not followed), anim_hands (no arms)
static bool event_now(bool *fp, bool *still, bool *anim_hands) {
    *fp = *still = *anim_hands = false;
    if (!framepace_in_event()) return false;
    int m = events_mode();
    if (m == EV_FIRST || m == EV_AUTO) {
        const vr_event_setting *s = event_setting(framepace_event_name());
        if (m == EV_FIRST || (s && s->fp)) {
            *fp = true;
            *still = !s || s->still;
            *anim_hands = !s || s->anim_hands;
        }
    }
    return true;
}

// First person: the eye follows Link's head down and up where it stays for a while - crouched (his head 0.68 m lower),
// swimming, on a horse - and not his steps: his head bone's height above his feet (vr_skel.c, as the animation has it;
// 1.45 m standing) is smoothed (a quarter second), and changes under 15 cm (a walk's bob: +-10 cm) are left out,
// growing to the full change at 30 cm. BetterVR lowers the view by a fixed 0.8 m crouching and moves it riding and
// swimming the same way. SAVAGEWIND_VR_HEAD_FOLLOW=0: the eye's height fixed, as before
#define VR_HEAD_STANDING 1.449f
static float head_follow(void) {
    static int on = -1;
    static float smooth;
    static uint64_t last_ns;
    if (on < 0) on = !(getenv("SAVAGEWIND_VR_HEAD_FOLLOW") && *getenv("SAVAGEWIND_VR_HEAD_FOLLOW") == '0');
    extern bool vr_skel_head_height(float *y);
    float y;
    uint64_t now = plat_now_ns();
    if (!on || !vr_skel_head_height(&y)) {
        smooth = 0, last_ns = 0;
        return 0;
    }
    float d = y - VR_HEAD_STANDING;
    d = d < -1.3f ? -1.3f : d > 0.6f ? 0.6f : d;
    float dt = last_ns ? (float)(now - last_ns) / 1e9f : 1.0f;
    last_ns = now;
    float k = 1 - expf(-(dt > 0.5f ? 0.5f : dt) / 0.25f);
    smooth += (d - smooth) * k;
    float a = fabsf(smooth), t = (a - 0.15f) / 0.15f;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    return smooth * t * t * (3 - 2 * t);
}

// ---- roomscale (BetterVR's: the player walking in the room walks Link) ----
// In first person, with the head more than 10 cm (horizontally) from Link's eye, the walk stick is pushed toward it,
// harder the farther (full at 40 cm), until it is within 4 cm: the game walks Link there, with its own collisions
// (BetterVR moves his body itself, casting against the world). The eye stays at the head meanwhile (vr_camera_lookat
// moves the neutral head with Link). Off while the player pushes the stick or plays an event; option VR_OPT_ROOMSCALE.
static void roomscale(vr_anchor a, vr_pose head, vr_vec3 geye, bool ev, const double *lp, const float *f) {
    if (c.fp_now) memcpy(c.rs.lp, lp, sizeof c.rs.lp), c.rs.have_lp = true;
    else c.rs.have_lp = false;
    vr_vec3 hw = vr_xr_to_game_point(a, head.p);
    float gx = hw.x - geye.x, gz = hw.z - geye.z, d = sqrtf(gx * gx + gz * gz);
    c.rs.gx = gx, c.rs.gz = gz;
    bool on = c.fp_now && !ev && vr_opt_on(VR_OPT_ROOMSCALE);
    uint64_t now = plat_now_ns();
    if (!on || d < 0.04f) c.rs.driving = false;
    else if (d > 0.10f && !c.rs.driving) c.rs.driving = true, c.rs.best = d, c.rs.best_ns = now;
    if (c.rs.driving && d < c.rs.best - 0.02f) c.rs.best = d, c.rs.best_ns = now;
    // he cannot get there (a wall, a rock, the water's pull) or the head is far off (leaning out of a chair, a recentre
    // gone stale): give up and put the view back over him (the room's head moved to his eye; BetterVR casts his body
    // against the world and stops there). Walking on would push him into the rock and leave the eye inside it
    if (c.rs.driving && (d > 0.6f || now - c.rs.best_ns > 700000000ull)) {
        c.neutral.p = vr_v3_add(c.neutral.p, vr_quat_rotate(vr_quat_conj(vr_anchor_rotation(a)), vr_v3(gx, 0, gz)));
        c.rs.driving = false, c.rs.gx = c.rs.gz = 0;
        static uint64_t said;
        if (now - said > 5000000000ull) said = now, LOG("[vr] roomscale: Link could not reach the head (%.2f m): the view back over him\n", d);
    }
    if (!c.rs.driving) {
        c.rs.x = c.rs.y = 0;
        return;
    }
    // the stick in the view's frame: ahead along the drawn view's heading, right across it
    float vy = vr_game_yaw_of(vr_v3(f[3] - f[0], 0, f[5] - f[2]));
    float ahead = (gx * sinf(vy) + gz * cosf(vy)) / d, right = (-gx * cosf(vy) + gz * sinf(vy)) / d;
    float m = (d - 0.04f) / 0.36f;
    m = m < 0.3f ? 0.3f : m > 1 ? 1 : m;
    c.rs.x = right * m, c.rs.y = ahead * m;
    c.rs.frames++;
}

// vr_input.c: the walk stick roomscale asks for now (false: none)
bool vr_roomscale_stick(float *x, float *y) {
    pthread_mutex_lock(&lock);
    bool on = c.rs.driving && vr_world_view();
    *x = c.rs.x, *y = c.rs.y;
    pthread_mutex_unlock(&lock);
    return on;
}
uint64_t vr_roomscale_frames(void) { return c.rs.frames; }

// vr_skel.c: Link's hands left to the event's animation now
bool vr_event_anim_hands(void) {
    bool fp, still, hands;
    return event_now(&fp, &still, &hands) && hands;
}

// framepace.c: the headset paces the game's frames (in VR with a session going)
bool vr_paces(void) { return vr_enabled() && vr_session_running(); }

bool vr_world_view(void) {
    if (!vr_enabled() || !vr_session_running()) return false;
    if (framepace_in_event()) {
        if (events_mode() == EV_SCREEN) return false;
        // an event held at 30 fps (framepace.c events_at_30: one of its waits needs every update) is drawn flat, one
        // frame a headset frame: in stereo it would get 15 a second in each eye
        if (framepace_event_held()) return false;
        // BetterVR's black bars: an event on its own camera (not in first person) shown flat, as the game frames it
        bool fp, still, hands;
        if (vr_opt(VR_OPT_EVENT_BARS) == 1 && event_now(&fp, &still, &hands) && !fp) return false;
    }
    if (framepace_title_ui() || framepace_loading_ui() || framepace_map_ui()) return false;
    // the Sheikah Slate's scope: on the virtual screen, as the game draws it - its zoom (the headset's own field undid
    // it), its lens and frame (BetterVR 1.0.1 shows it flat). Up while its lens drew in the last few frames
    // (nvn/vulkan/exec.c scope_mark). SAVAGEWIND_VR_SCOPE_3D=1: in the eyes as play
    static int scope_3d = -1;
    if (scope_3d < 0) scope_3d = getenv("SAVAGEWIND_VR_SCOPE_3D") && *getenv("SAVAGEWIND_VR_SCOPE_3D") == '1';
    extern uint64_t vk_scope_frame(void);
    extern uint64_t renderer_present_count(void);
    uint64_t sf = vk_scope_frame();
    if (!scope_3d && sf && renderer_present_count() + 1 < sf + 6) return false;
    if (g_site.pause_state && LD32(g_site.pause_state) != 0) return false;
    // Savage Wind's own overlay menu (Options, Controls...) is drawn on the window's picture, which the eyes do not get:
    // while it is open the headset shows that picture on the virtual screen
    extern bool menu_is_open(void);
    if (menu_is_open()) return false;
    // Link in the world: the boot's logos come before the start screen is seen as such (framepace_title_ui), and the
    // eyes, stereo and the head on their camera are for play (read once a presented frame: this is asked often)
    // (an event plays in the world even before Link is placed in it: the new game's opening, Demo169_0)
    if (framepace_in_event()) return true;
    extern bool output_player_exists(void);
    extern uint64_t renderer_present_count(void);
    static uint64_t asked = ~0ull;
    static bool player;
    uint64_t now = renderer_present_count();
    if (now != asked) asked = now, player = output_player_exists();
    return player;
}

void vr_recenter(void) {
    pthread_mutex_lock(&lock);
    c.recenter = true;
    pthread_mutex_unlock(&lock);
}

void vr_turn(float radians) {
    pthread_mutex_lock(&lock);
    c.turn = remainderf(c.turn + radians, 2 * VR_PI);
    pthread_mutex_unlock(&lock);
}

void vr_window_aspect(float a) {
    if (a > 0.1f && a < 10) c.window_aspect = a;
}

// runtime/hle/framepace.c rt_vfr_update, at the start of each game frame: which eye this frame is, and the game's
// step for it (ratio: console frames of game time)
//
// The game calls this and sets its cameras in either order within a frame, so the eye is chosen by whichever comes
// first after the last present (vr_present_mark): the frame's eye is fixed once its first camera is set, until then it
// is the eye that comes next.
float vr_frame_ratio(float ratio, bool paused) {
    bool world = !paused && vr_world_view();
    if (!world || !stereo_on()) return ratio;
    pthread_mutex_lock(&lock);
    float step = vr_pair_step(&c.pair, ratio);  // (the pair's time in its first frame, nearly none in its second)
    trace("frame", c.pair.eye, c.cam_set);
    pthread_mutex_unlock(&lock);
    return step;
}

static vr_pose from_xr(XrPosef p) {
    vr_pose r = {{p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w},
                 {p.position.x, p.position.y, p.position.z}};
    return r;
}

static XrPosef to_xr(vr_pose p) {
    XrPosef r = {{p.q.x, p.q.y, p.q.z, p.q.w}, {p.p.x, p.p.y, p.p.z}};
    return r;
}

// both eyes at the time the frame being made should be shown
static bool locate(XrView v[2]) {
    XrTime t = vr_next_display_time();
    XrSession s = vr_xr_session();
    if (!t || s == XR_NULL_HANDLE) return false;
    XrViewLocateInfo li = {XR_TYPE_VIEW_LOCATE_INFO, NULL, XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO, t, vr_xr_local()};
    XrViewState vs = {XR_TYPE_VIEW_STATE};
    v[0] = (XrView){XR_TYPE_VIEW};
    v[1] = (XrView){XR_TYPE_VIEW};
    uint32_t n = 0;
    if (XR_FAILED(xrLocateViews(s, &li, &vs, 2, &n, v)) || n != 2) return false;
    return (vs.viewStateFlags & XR_VIEW_STATE_ORIENTATION_VALID_BIT) != 0;
}

static bool near9(const float *a, const float *b) {
    for (int i = 0; i < 9; i++)
        if (fabsf(a[i] - b[i]) > 1e-4f) return false;
    return true;
}

// (reverse engineering, `vr`) the last view camera given the head: its sead::LookAtCamera (f - 0x38)
static _Atomic uint64_t last_cam;
uint64_t vr_lookat_camera(void) { return last_cam; }

// rt_lookat, for a view camera (eye off the origin, up near +y): f = eye[3], at[3], up[3]
void vr_camera_lookat(float *f) {
    last_cam = (uint64_t)(uintptr_t)f - 0x38;
    if (!vr_world_view()) {
        c.out_ok = false;
        c.fp_now = false;   // (menus: Link's model as the game has it, the inventory's too)
        return;
    }
    pthread_mutex_lock(&lock);
    if (!(c.out_ok && near9(f, c.out))) memcpy(c.game, f, sizeof c.game);  // (else: ours, the game's is kept)
    XrView v[2];
    if (!locate(v)) {
        pthread_mutex_unlock(&lock);
        return;
    }
    // the head: halfway between the eyes, turned as the first one (the runtime turns both alike)
    vr_pose head = from_xr(v[0].pose);
    head.p = vr_v3_scale(vr_v3_add(head.p, from_xr(v[1].pose).p), 0.5f);
    if (!c.have_neutral || c.recenter) {
        c.neutral = head;
        c.have_neutral = true;
        c.recenter = false;
        LOG("[vr] recentred: head at %.2f %.2f %.2f, heading %.1f deg\n", head.p.x, head.p.y, head.p.z,
            vr_quat_heading(head.q) * 57.29578f);
    }
    int eye = stereo_on() ? vr_pair_camera(&c.pair) : -1;
    c.cam_set = true;
    trace("lookat", eye, c.cur.world);
    vr_pose view = eye >= 0 ? from_xr(v[eye].pose) : head;
    // the game's camera: where it is and the way it looks along the ground
    const float *gf = c.game;
    vr_vec3 geye = vr_v3(gf[0], gf[1], gf[2]);
    float yaw = vr_game_yaw_of(vr_v3(gf[3] - gf[0], gf[4] - gf[1], gf[5] - gf[2]));
    // first person: the neutral head goes to Link's eyes, a little ahead of his head, facing the game camera's way
    // an event: first person or its camera (event_now); a still one keeps the turn from before it
    bool ev_fp, ev_still, ev_hands, ev = event_now(&ev_fp, &ev_still, &ev_hands);
    if (ev && !c.in_event) {
        c.event_yaw = c.last_yaw;
        LOG("[vr] event %s: %s%s\n", framepace_event_name(), ev_fp ? "first person" : "its camera",
            ev_fp && ev_still ? ", the view kept still" : "");
    }
    c.in_event = ev;
    if (ev && ev_fp && ev_still) yaw = c.event_yaw;
    else c.last_yaw = yaw;
    bool fp = ev ? ev_fp : first_person();
    double lp[3];
    c.fp_now = false;
    if (fp && control_cell_get(&control_cell_player_pos, lp)) {
        // Seated: the centred head at Link's eyes. Standing (BetterVR's): the centred head's real height above the floor
        // (LOCAL's origin above STAGE's, plus the head's height in LOCAL), so a shorter or crouching player sees lower
        float h = c.eye_height, ly;
        extern bool vr_local_height(float *y);
        if (vr_opt(VR_OPT_PLAY_POSITION) == 1 && vr_local_height(&ly)) {
            h = c.neutral.p.y + ly;
            h = h < 0.4f ? 0.4f : h > 2.4f ? 2.4f : h;
        }
        h += head_follow();
        c.eye_used = h;
        // (the eye ahead of his head's centre the way the head looks, not the game's camera: looking back, it was
        // behind him and saw his back)
        float look = yaw + c.turn + remainderf(vr_quat_heading(head.q) - vr_quat_heading(c.neutral.q), 2 * VR_PI);
        geye = vr_v3((float)lp[0] + sinf(look) * c.forward,
                     (float)lp[1] + h + vr_opt(VR_OPT_HEIGHT) / 100.0f,   // (the Options page's height)
                     (float)lp[2] + cosf(look) * c.forward);
        c.fp_now = true;
    } else if (!ev && control_cell_get(&control_cell_player_pos, lp)) {
        // third person: the game's camera moved toward Link's head or away from it (BetterVR's ThirdPlayerDistance;
        // the Options page's Third-person distance, % of the game's own), along the line between them
        int k = vr_opt(VR_OPT_THIRD_DISTANCE);
        if (k > 0 && k != 100) {
            vr_vec3 head = vr_v3((float)lp[0], (float)lp[1] + 1.5f, (float)lp[2]);
            geye = vr_v3_add(head, vr_v3_scale(vr_v3_sub(geye, head), k / 100.0f));
        }
    }
    // roomscale (BetterVR's): Link walked toward the head since the last camera: the neutral head follows him, so the
    // eye stays where the player's head is in the world while his body catches up. Only his step toward the head, and
    // no farther than it: a slope, a current or a push moving him elsewhere moves the eye with him (the eye pinned in
    // the world while he slid away left the view off his body, and the stick kept walking him)
    if (c.fp_now && c.rs.driving && c.rs.have_lp && c.anchor_ok) {
        float dx = (float)(lp[0] - c.rs.lp[0]), dz = (float)(lp[2] - c.rs.lp[2]);
        float d = sqrtf(c.rs.gx * c.rs.gx + c.rs.gz * c.rs.gz);
        if (d > 1e-3f && dx * dx + dz * dz < 1.0f) {
            float s = (dx * c.rs.gx + dz * c.rs.gz) / d;
            s = s < 0 ? 0 : s > d ? d : s;
            vr_vec3 dl = vr_v3(c.rs.gx / d * s, 0, c.rs.gz / d * s);
            c.neutral.p = vr_v3_add(c.neutral.p, vr_quat_rotate(vr_quat_conj(vr_anchor_rotation(c.anchor)), dl));
        }
    }
    // the anchor that puts the neutral head at the game's eye, looking the game's way; the eye's pose from there
    vr_anchor a = vr_anchor_recenter(c.neutral, geye, yaw + c.turn, 1.0f);
    c.anchor = a, c.anchor_ok = true;
    c.anchor_lp_ok = c.fp_now;
    if (c.fp_now) memcpy(c.anchor_lp, lp, sizeof c.anchor_lp);
    vr_lookat_from_view(a, view, f, f + 3, f + 6);
    roomscale(a, head, geye, ev, lp, f);
    memcpy(c.out, f, sizeof c.out);
    c.out_ok = true;
    // the frustum. In stereo, the eye's own field, off-centre as it is (narrower on the nose's side: SAVAGEWIND_VR_
    // ASYMMETRIC=0 for the symmetric one), widened to the window's shape about its centre: the game's projection gets
    // its half-size and its centre as an offset (vr_persp, vr_persp_offset). In mono (one picture for both eyes): both
    // fields together, made symmetric.
    static int asym = -1;
    if (asym < 0) asym = !(getenv("SAVAGEWIND_VR_ASYMMETRIC") && *getenv("SAVAGEWIND_VR_ASYMMETRIC") == '0');
    float tx = 0, ty = 0, cx = 0, cy = 0;
    if (eye >= 0 && asym) {
        float l = tanf(v[eye].fov.angleLeft), r = tanf(v[eye].fov.angleRight);
        float u = tanf(v[eye].fov.angleUp), d = tanf(v[eye].fov.angleDown);
        tx = (r - l) / 2, ty = (u - d) / 2, cx = (r + l) / 2, cy = (u + d) / 2;
    } else {
        for (int i = 0; i < 2; i++) {
            if (eye >= 0 && i != eye) continue;
            tx = fmaxf(tx, fmaxf(tanf(v[i].fov.angleRight), tanf(-v[i].fov.angleLeft)));
            ty = fmaxf(ty, fmaxf(tanf(v[i].fov.angleUp), tanf(-v[i].fov.angleDown)));
        }
    }
    if (tx > 0.05f && ty > 0.05f) {
        float wa = c.window_aspect;
        if (tx / ty < wa) tx = ty * wa;
        else ty = tx / wa;
        c.tan_x = tx, c.tan_y = ty, c.off_x = cx, c.off_y = cy;
        c.cur = (vr_view){true, eye, to_xr(view), {atanf(cx - tx), atanf(cx + tx), atanf(cy + ty), atanf(cy - ty)}};
    }
    c.updates++;
    // (debugging) SAVAGEWIND_VR_LOG_CAMERA=<n>: every n-th update, the eye, the game's camera and the view made
    static int log_every = -1;
    if (log_every < 0) log_every = getenv("SAVAGEWIND_VR_LOG_CAMERA") ? atoi(getenv("SAVAGEWIND_VR_LOG_CAMERA")) : 0;
    if (log_every > 0 && c.updates % (uint64_t)log_every == 0) {
        vr_vec3 od = vr_v3(f[3] - f[0], f[4] - f[1], f[5] - f[2]);
        LOG("[vr-cam] eye %d head %.2f %.2f %.2f heading %.1f | game eye %.1f %.1f %.1f yaw %.1f | view yaw %.1f pitch "
            "%.1f eye %.2f %.2f %.2f\n", eye, head.p.x, head.p.y, head.p.z, vr_quat_heading(head.q) * 57.29578f, geye.x,
            geye.y, geye.z, yaw * 57.29578f, vr_game_yaw_of(od) * 57.29578f, vr_game_pitch_of(od) * 57.29578f, f[0],
            f[1], f[2]);
    }
    pthread_mutex_unlock(&lock);
}

// rt_persp, the world camera (far plane over 10000): its tan(fovy / 2) and aspect in play
// output_scale.c rt_persp_offset, the world camera's: its projection moved so that its centre is the frustum's
// (vr_camera_lookat), as fractions of the image's width and height (NDC is 2 wide). SAVAGEWIND_VR_OFFSET_SIGN=-1 flips
// them (a check of the sign).
bool vr_persp_offset(float *x, float *y) {
    if (!vr_world_view()) return false;
    static float sign = 0;
    if (!sign) sign = getenv("SAVAGEWIND_VR_OFFSET_SIGN") && atoi(getenv("SAVAGEWIND_VR_OFFSET_SIGN")) < 0 ? -1.0f : 1.0f;
    pthread_mutex_lock(&lock);
    bool ok = c.cur.world && c.tan_x > 0 && c.tan_y > 0;
    if (ok) *x += sign * c.off_x / (2 * c.tan_x), *y += sign * c.off_y / (2 * c.tan_y);
    pthread_mutex_unlock(&lock);
    return ok;
}

bool vr_persp(float *tan_fovy, float *aspect) {
    if (!vr_world_view()) return false;
    pthread_mutex_lock(&lock);
    bool ok = c.cur.world;
    trace("persp", c.cur.eye, ok);
    if (ok) *tan_fovy = c.tan_y, *aspect = c.tan_x / c.tan_y;
    pthread_mutex_unlock(&lock);
    return ok;
}

// nvnQueuePresentTexture (the game's thread): this frame is done, as what it was drawn
void vr_present_mark(void) {
    if (!vr_enabled()) return;
    pthread_mutex_lock(&lock);
    if (c.q_count == QUEUE) {  // (never in practice: the queue thread is a frame or two behind)
        c.q_head = (c.q_head + 1) % QUEUE;
        c.q_count--;
    }
    vr_view v = c.cur;
    v.world = v.world && c.cam_set && vr_world_view();  // (a frame without a camera of its own: the screen)
    c.q[(c.q_head + c.q_count++) % QUEUE] = v;
    trace("present", v.eye, v.world);
    // the next frame: the other eye after a left one, else the left
    if (stereo_on()) vr_pair_present(&c.pair, v.world);
    c.cam_set = false;
    pthread_mutex_unlock(&lock);
}

// the present on the queue thread (device.c backend_present): what the frame being presented is
bool vr_present_take(vr_view *out) {
    pthread_mutex_lock(&lock);
    bool ok = c.q_count > 0;
    if (ok) {
        *out = c.q[c.q_head];
        c.q_head = (c.q_head + 1) % QUEUE;
        c.q_count--;
    }
    pthread_mutex_unlock(&lock);
    if (!ok) memset(out, 0, sizeof *out);
    return ok;
}

uint64_t vr_camera_updates(void) { return c.updates; }
uint64_t vr_stereo_pairs(void) { return c.pair.pairs; }

// vr_skel.c: the last camera was set in first person (the eye in Link's head)
bool vr_first_person_now(void) { return c.fp_now; }
float vr_eye_height_used(void) { return c.eye_used; }

// vr_skel.c: a tracking-space pose in the game's world, with the anchor the last camera used (false before one)
// vr_skel.c: the way the head looks in the game's world, flat (radians, the game's yaw: x = sin, z = cos), from the
// last camera - first person only
bool vr_view_heading(float *yaw) {
    pthread_mutex_lock(&lock);
    bool ok = c.out_ok && c.fp_now;
    if (ok) {
        float dx = c.out[3] - c.out[0], dz = c.out[5] - c.out[2];
        ok = dx * dx + dz * dz > 1e-8f;
        if (ok) *yaw = atan2f(dx, dz);
    }
    pthread_mutex_unlock(&lock);
    return ok;
}

// The anchor is the last camera's; Link's skeleton and the actors are calculated before this frame's camera, after
// his move, so on the move his arms (and what they hold) were placed one step behind the eye - at a run, on a horse,
// the hands slid away from where the controllers are. The anchor is carried along by how far Link has moved since
// that camera (BetterVR's GetFreshCameraReferenceMtx). SAVAGEWIND_VR_FRESH_ANCHOR=0: the last camera's as it was
bool vr_tracking_to_world(const vr_pose *in, vr_pose *out) {
    static int fresh = -1;
    if (fresh < 0) fresh = !(getenv("SAVAGEWIND_VR_FRESH_ANCHOR") && *getenv("SAVAGEWIND_VR_FRESH_ANCHOR") == '0');
    double lp[3];
    bool now = fresh && control_cell_get(&control_cell_player_pos, lp);
    pthread_mutex_lock(&lock);
    bool ok = c.anchor_ok && c.fp_now;
    if (ok) {
        *out = vr_xr_to_game_pose(c.anchor, *in);
        if (now && c.anchor_lp_ok) {
            vr_vec3 d = vr_v3((float)(lp[0] - c.anchor_lp[0]), (float)(lp[1] - c.anchor_lp[1]),
                              (float)(lp[2] - c.anchor_lp[2]));
            if (vr_v3_len(d) < 2.0f) out->p = vr_v3_add(out->p, d);   // (a warp or a reload: no carry)
        }
    }
    pthread_mutex_unlock(&lock);
    return ok;
}

// xr_vulkan.c: the heading the head had when it was centred (the body's way, for a HUD that does not follow the gaze)
bool vr_neutral_heading(float *heading) {
    pthread_mutex_lock(&lock);
    bool ok = c.have_neutral;
    if (ok) *heading = vr_quat_heading(c.neutral.q);
    pthread_mutex_unlock(&lock);
    return ok;
}

// exec.c (the game's thread, translating the frame's commands): the eye the frame in progress is drawn for, in play in
// stereo (0 left, 1 right; -1 otherwise). Fixed by the frame's first camera (vr_pair_camera), before its passes.
int vr_frame_eye(void) {
    if (!vr_world_view() || !stereo_on()) return -1;
    pthread_mutex_lock(&lock);
    int eye = c.cam_set ? vr_pair_eye(&c.pair) : -1;
    pthread_mutex_unlock(&lock);
    return eye;
}

// exec.c (the game's thread, at the runes' target pick): the point of the frame in progress's picture the rune
// aims at, as the pick's coordinates (u 0..1 left to right, v 0..1 top to bottom). The game picks Stasis', Magnesis'
// and Cryonis' target by reading its G-buffer at the picture's centre (a 1x1 draw, its constants' first two floats
// 0.5 0.5). In VR the picture's centre is not where the eye looks: each eye's field is off-centre (BetterVR's
// patch_CTRL_FixScreenChecks moves the point onto the eye's axis on the Wii U). With the option on, the point is where
// the main hand's ray (the grip's forward, 30 m out) lands on the eye's picture; with it off
// (SAVAGEWIND_VR_RUNE_AIM=head), where the eye's own axis does. Kept a little inside the picture's edges. false (the
// game's centre) out of the headset's view of play.
bool vr_hand_pose(int hand, vr_pose *out);   // vr_input.c
static _Atomic uint64_t rune_aimed_ns;   // (the last pick aimed by the hand: plat_now_ns)
bool vr_rune_aim_uv(float *u, float *v) {
    if (!vr_world_view()) return false;
    pthread_mutex_lock(&lock);
    vr_view view = c.cur;
    pthread_mutex_unlock(&lock);
    if (!view.world) return false;
    vr_pose eye = from_xr(view.pose), hand;
    vr_vec3 from = eye.p, dir = vr_quat_rotate(eye.q, vr_v3(0, 0, -1));
    if (vr_opt(VR_OPT_RUNE_AIM) == 0 && vr_hand_pose(vr_opt(VR_OPT_LEFT_HANDED) == 1 ? 0 : 1, &hand)) {
        from = hand.p, dir = vr_quat_rotate(hand.q, vr_v3(0, 0, -1));
        atomic_store(&rune_aimed_ns, plat_now_ns());
    }
    float x, y;
    if (!vr_ray_picture_uv(eye, from, dir, 30.0f, view.fov.angleLeft, view.fov.angleRight, view.fov.angleUp,
                           view.fov.angleDown, &x, &y))
        return false;
    *u = x < 0.02f ? 0.02f : x > 0.98f ? 0.98f : x;
    *v = y < 0.02f ? 0.02f : y > 0.98f ? 0.98f : y;
    return true;
}

// xr_vulkan.c (the bow arc's dots): while a rune is aimed by the hand (a pick aimed in the last 0.15 s), its ray as
// LOCAL space points from the main hand out to 12 m, denser near the hand: the game's reticle stays at the view's
// centre, these show what the hand picks. 0 points otherwise.
int vr_rune_ray(float (*pts)[3], int max) {
    uint64_t now = plat_now_ns(), last = atomic_load(&rune_aimed_ns);
    if (!last || now - last > 150000000ull || vr_opt(VR_OPT_RUNE_AIM) != 0) return 0;
    vr_pose hand;
    if (!vr_hand_pose(vr_opt(VR_OPT_LEFT_HANDED) == 1 ? 0 : 1, &hand)) return 0;
    vr_vec3 d = vr_quat_rotate(hand.q, vr_v3(0, 0, -1));
    int n = 0;
    for (int i = 1; n < max; i++) {
        float s = 0.15f + 0.05f * (float)(i * i);
        if (s > 12.0f) break;
        vr_vec3 p = vr_v3_add(hand.p, vr_v3_scale(d, s));
        pts[n][0] = p.x, pts[n][1] = p.y, pts[n][2] = p.z;
        n++;
    }
    return n;
}

// output_scale.c (TAA's jitter): in play in stereo, frames in pairs
bool vr_stereo_now(void) { return vr_world_view() && stereo_on(); }

// runtime/hle/actor_jobs.c: in stereo play an actor's job-push skip (counted in game frames) lasts twice the frames, as
// long as flat (SAVAGEWIND_VR_JOB_SKIP=0: the game's count)
bool vr_job_skip_doubled(void) {
    static int on = -1;
    if (on < 0) on = !(getenv("SAVAGEWIND_VR_JOB_SKIP") && *getenv("SAVAGEWIND_VR_JOB_SKIP") == '0');
    if (!on || !vr_stereo_now()) return false;
    static _Atomic uint64_t n;
    if (n++ == 0) LOG("[vr] stereo: actors' job-push skips doubled (two game frames a moment)\n");
    return true;
}

// mvec.c (TAA, the game's thread at the frame's composite): the offset vr_persp_offset gives the frame being drawn
// (fractions of the picture), to tell it from the jitter
bool vr_offset_now(float *x, float *y) {
    *x = *y = 0;
    if (!vr_world_view()) return false;
    pthread_mutex_lock(&lock);
    bool ok = c.cur.world && c.tan_x > 0 && c.tan_y > 0;
    if (ok) *x = c.off_x / (2 * c.tan_x), *y = c.off_y / (2 * c.tan_y);
    pthread_mutex_unlock(&lock);
    return ok;
}
