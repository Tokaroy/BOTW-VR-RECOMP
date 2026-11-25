// Synchronous stereo (in progress, docs/vr/SYNC_STEREO.md): one game frame a stereo pair, its draws translated once
// for each eye, the right eye's with its own camera. As BetterVR 1.0.1 does on the Wii U (its Cemu repeats every draw
// of a stereo scope for the right view, with the right view's constants: resources/BreathOfTheWild_BetterVR/src and its
// Cemu's LatteView.cpp), here the translating thread (runtime/nvn/vulkan/exec.c) would run the frame's command lists
// twice.
//
// Step 1, the census (SAVAGEWIND_VR_SYNC_CENSUS=1): where the game's camera is in the constant buffers its draws read.
// Every few seconds, for one short window, each constant buffer a draw binds is searched for the view matrices of the
// last frames (sead::Camera's Matrix34f at camera + 0x8, row-major 3x4, read here when rt_lookat is called next: the
// game updates it right after) in the shapes the shaders may use: a row of the view (with its translation), minus its
// third row (the w row of a view-projection), a column (the inverse view's rows, or a column-major view), the eye's
// position, the view direction, and three numbers proportional to it (a view-projection's z row). Logged as
// "[vr-sync] census": shader, stage, buffer, offset, what was found, how many times, the target's size.
#include <math.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../rt.h"

uint64_t plat_now_ns(void);

#define RING 6
static float ring[RING][12];
static int ring_n, ring_head;
static pthread_mutex_t ring_lock = PTHREAD_MUTEX_INITIALIZER;

static int census_on(void) {
    static int on = -1;
    if (on < 0) on = getenv("SAVAGEWIND_VR_SYNC_CENSUS") && *getenv("SAVAGEWIND_VR_SYNC_CENSUS") == '1';
    return on;
}

// sead::LookAtCamera::doUpdateMatrix's view (row-major 3x4) from eye, at, up: z = eye - at, x = up x z, y = z x x
void vr_sync_lookat_matrix(const float *f, float *m) {
    float z[3] = {f[0] - f[3], f[1] - f[4], f[2] - f[5]};
    float zl = sqrtf(z[0] * z[0] + z[1] * z[1] + z[2] * z[2]);
    for (int i = 0; i < 3; i++) z[i] /= zl;
    float x[3] = {f[7] * z[2] - f[8] * z[1], f[8] * z[0] - f[6] * z[2], f[6] * z[1] - f[7] * z[0]};
    float xl = sqrtf(x[0] * x[0] + x[1] * x[1] + x[2] * x[2]);
    for (int i = 0; i < 3; i++) x[i] /= xl;
    float y[3] = {z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]};
    const float *r[3] = {x, y, z};
    for (int i = 0; i < 3; i++) {
        m[4 * i] = r[i][0], m[4 * i + 1] = r[i][1], m[4 * i + 2] = r[i][2];
        m[4 * i + 3] = -(r[i][0] * f[0] + r[i][1] * f[1] + r[i][2] * f[2]);
    }
}

// (SAVAGEWIND_VR_SYNC_CHECK=1) the view the last camera was given (vr_camera_lookat's output), to compare with the
// matrix the game made from it (vr_sync_note_camera, at the camera's next update)
static float last_out[9];
static bool last_out_ok;
void vr_sync_note_out(const float *f) { memcpy(last_out, f, sizeof last_out), last_out_ok = true; }

// rt_lookat (vr_camera_lookat), before the game recomputes the view: the matrix there is the one it computed last time
void vr_sync_note_camera(const float *f) {
    const float *m = (const float *)((const char *)f - 0x38 + 0x8);
    static int check = -1;
    if (check < 0) check = getenv("SAVAGEWIND_VR_SYNC_CHECK") && *getenv("SAVAGEWIND_VR_SYNC_CHECK") == '1';
    if (check && last_out_ok) {
        static uint64_t said, n;
        static float worst;
        float mine[12], d = 0;
        vr_sync_lookat_matrix(last_out, mine);
        for (int i = 0; i < 12; i++) d = fmaxf(d, fabsf(mine[i] - m[i]) / (1 + fabsf(m[i])));
        worst = fmaxf(worst, d), n++;
        uint64_t now = plat_now_ns();
        if (now - said > 2000000000ull) {
            said = now;
            LOG("[vr-sync] check: the view from eye/at/up against the game's, worst relative difference %.2e over %llu "
                "(game row0 %.6f %.6f %.6f %.4f, ours %.6f %.6f %.6f %.4f)\n", worst, (unsigned long long)n, m[0], m[1],
                m[2], m[3], mine[0], mine[1], mine[2], mine[3]);
            worst = 0, n = 0;
        }
    }
    if (!census_on()) return;
    float n = m[0] * m[0] + m[1] * m[1] + m[2] * m[2];
    if (!(n > 0.98f && n < 1.02f)) return;   // (not a rotation yet)
    // (cameras along the axes - the cube map's faces - are not the view, and match every identity matrix)
    if (fabsf(m[0]) > 0.999f || fabsf(m[0]) < 1e-3f || fabsf(m[2]) < 1e-3f || fabsf(m[9]) < 1e-3f) return;
    pthread_mutex_lock(&ring_lock);
    int last = (ring_head + RING - 1) % RING;
    if (!ring_n || memcmp(ring[last], m, 48)) {
        memcpy(ring[ring_head], m, 48);
        ring_head = (ring_head + 1) % RING;
        if (ring_n < RING) ring_n++;
    }
    pthread_mutex_unlock(&ring_lock);
}

enum { K_ROW0, K_ROW1, K_ROW2, K_NEGROW2, K_COL0, K_COL1, K_COL2, K_COLS4, K_EYE, K_DIR, K_ZPROP, K_COUNT };
static const char *const kname[K_COUNT] = {"row0", "row1", "row2", "-row2", "col0", "col1", "col2", "colmajor",
                                           "eye", "dir", "zprop"};

typedef struct { uint64_t prog; uint32_t off; uint8_t stage, k, kind, used; uint32_t count, w, h; } Hit;
#define NHIT 4096
static Hit hits[NHIT];
static uint64_t win_start, next_win, windows, buffers_scanned;
static bool in_win;

static bool close1(float a, float b) { return fabsf(a - b) <= 2e-5f + 2e-5f * fabsf(b); }

static void note(uint64_t prog, int stage, int k, uint32_t off, int kind, int w, int h) {
    uint64_t key = (prog * 31 + stage) * 131 + k * 7 + kind + (uint64_t)off * 2654435761u;
    for (int i = 0; i < 64; i++) {
        Hit *e = &hits[(key + i) % NHIT];
        if (e->used && e->prog == prog && e->off == off && e->stage == stage && e->k == k && e->kind == kind) {
            e->count++;
            return;
        }
        if (!e->used) {
            *e = (Hit){prog, off, (uint8_t)stage, (uint8_t)k, (uint8_t)kind, 1, 1, (uint32_t)w, (uint32_t)h};
            return;
        }
    }
}

static int cmp_hit(const void *a, const void *b) {
    const Hit *x = a, *y = b;
    if (x->used != y->used) return y->used - x->used;
    if (x->prog != y->prog) return x->prog < y->prog ? -1 : 1;
    if (x->stage != y->stage) return x->stage - y->stage;
    if (x->k != y->k) return x->k - y->k;
    return x->off < y->off ? -1 : x->off > y->off;
}

static void report(void) {
    int n = 0;
    for (int i = 0; i < NHIT; i++) n += hits[i].used;
    qsort(hits, NHIT, sizeof *hits, cmp_hit);
    LOG("[vr-sync] census %llu: %llu buffers searched, %d places with the camera in them\n", (unsigned long long)windows,
        (unsigned long long)buffers_scanned, n);
    for (int i = 0; i < n; i++) {
        Hit *e = &hits[i];
        LOG("[vr-sync]   shader %llx stage %d cbuf %d +%#x %s x%u (target %ux%u)\n", (unsigned long long)e->prog, e->stage,
            e->k, e->off, kname[e->kind], e->count, e->w, e->h);
    }
    memset(hits, 0, sizeof hits);
    buffers_scanned = 0;
}

// exec.c cbuf_info: constant buffer k of a draw's stage, its bytes as the draw will read them
void vr_sync_census(uint64_t prog, int stage, int k, const void *data, uint64_t size, int w, int h) {
    if (!census_on()) return;
    uint64_t now = plat_now_ns();
    if (!next_win) next_win = now + 20000000000ull;   // (the first after 20 s: in play)
    if (now >= next_win) {
        win_start = now;
        next_win = now + 4000000000ull;
        in_win = true;
    }
    if (!in_win) return;
    if (now - win_start > 30000000ull) {   // (a window: 30 ms, about a pair of frames)
        in_win = false;
        if (++windows % 3 == 0) report();   // (three windows a report)
        return;
    }
    float m[RING][12];
    int nm;
    pthread_mutex_lock(&ring_lock);
    nm = ring_n;
    memcpy(m, ring, sizeof m);
    pthread_mutex_unlock(&ring_lock);
    if (!nm) return;
    buffers_scanned++;
    const float *d = data;
    int n = (int)(size / 4);
    for (int j = 0; j < nm; j++) {
        const float *v = m[j];
        float eye[3];   // e = -R^T t
        for (int a = 0; a < 3; a++) eye[a] = -(v[0 + a] * v[3] + v[4 + a] * v[7] + v[8 + a] * v[11]);
        for (int i = 0; i + 3 <= n; i++) {
            float x = d[i];
            if (x == 0 || !isfinite(x)) continue;
            for (int r = 0; r < 3; r++)   // rows (with their translation)
                if (i + 4 <= n && close1(x, v[4 * r]) && close1(d[i + 1], v[4 * r + 1]) && close1(d[i + 2], v[4 * r + 2]) &&
                    close1(d[i + 3], v[4 * r + 3]) && fabsf(v[4 * r]) > 1e-3f)
                    note(prog, stage, k, i * 4, K_ROW0 + r, w, h);
            if (i + 4 <= n && close1(x, -v[8]) && close1(d[i + 1], -v[9]) && close1(d[i + 2], -v[10]) && close1(d[i + 3], -v[11]))
                note(prog, stage, k, i * 4, K_NEGROW2, w, h);
            for (int col = 0; col < 3; col++)   // columns contiguous: the inverse view's rows
                if (close1(x, v[col]) && close1(d[i + 1], v[4 + col]) && close1(d[i + 2], v[8 + col]) && fabsf(v[col]) > 1e-3f)
                    note(prog, stage, k, i * 4, K_COL0 + col, w, h);
            if (i + 9 <= n && close1(x, v[0]) && close1(d[i + 4], v[1]) && close1(d[i + 8], v[2]) && close1(d[i + 1], v[4]) &&
                fabsf(v[0]) > 1e-3f)   // column-major (stride 4)
                note(prog, stage, k, i * 4, K_COLS4, w, h);
            if (close1(x, eye[0]) && close1(d[i + 1], eye[1]) && close1(d[i + 2], eye[2]))
                note(prog, stage, k, i * 4, K_EYE, w, h);
            if (close1(x, -v[8]) && close1(d[i + 1], -v[9]) && close1(d[i + 2], -v[10]) && !(i + 4 <= n && close1(d[i + 3], -v[11])))
                note(prog, stage, k, i * 4, K_DIR, w, h);   // (the view direction: minus the third row)
            if (fabsf(v[8]) > 0.05f && fabsf(v[10]) > 0.05f) {   // proportional to the third row, not equal (+-)
                float s = x / v[8];
                if (fabsf(s) > 1e-3f && !close1(fabsf(s), 1) && close1(d[i + 1], s * v[9]) && close1(d[i + 2], s * v[10]))
                    note(prog, stage, k, i * 4, K_ZPROP, w, h);
            }
        }
    }
}

// ---- the right eye's pass (SAVAGEWIND_VR_SYNC=1) ----
// vr_camera.c, for each left frame: its camera (f0: eye, at, up as given to the game), the right eye's (f1) and each
// eye's field (tan half-width, half-height, centre x, y) - kept by pair id until the translator's replay of the frame
typedef struct { uint64_t id; float f0[9], f1[9], t0[4], t1[4], vl[12], il[12]; } SyncFrame;
static void inv_view(const float *v, float *o);
#define SYNC_FRAMES 16
static SyncFrame frames[SYNC_FRAMES];
static unsigned frames_next;
static pthread_mutex_t frames_lock = PTHREAD_MUTEX_INITIALIZER;

void vr_sync_frame(uint64_t pair_id, const float *f0, const float *f1, const float t0[4], const float t1[4]) {
    pthread_mutex_lock(&frames_lock);
    SyncFrame *s = &frames[frames_next++ % SYNC_FRAMES];
    s->id = pair_id;
    memcpy(s->f0, f0, sizeof s->f0), memcpy(s->f1, f1, sizeof s->f1);
    memcpy(s->t0, t0, sizeof s->t0), memcpy(s->t1, t1, sizeof s->t1);
    vr_sync_lookat_matrix(f0, s->vl);
    inv_view(s->vl, s->il);
    pthread_mutex_unlock(&frames_lock);
}

// exec.c, the left pass: the vec4 rows (of the first 256) of a constant buffer that hold the camera of one of the last
// frames (its view or inverse: three rows each); false when none
bool vr_sync_camera_rows(const void *src, uint64_t size, uint64_t rows[4]) {
    rows[0] = rows[1] = rows[2] = rows[3] = 0;
    bool any = false;
    float m[SYNC_FRAMES][24], e[SYNC_FRAMES][3];
    int nm = 0;
    pthread_mutex_lock(&frames_lock);
    for (int k = 0; k < SYNC_FRAMES; k++) {   // (all kept: after a stall the game can be several frames ahead)
        const SyncFrame *f = &frames[(frames_next + SYNC_FRAMES - 1 - k) % SYNC_FRAMES];
        if (!f->id) continue;
        memcpy(m[nm], f->vl, 48), memcpy(m[nm] + 12, f->il, 48), memcpy(e[nm], f->f0, 12), nm++;
    }
    pthread_mutex_unlock(&frames_lock);
    const float *d = src;
    int n = (int)(size / 4);
    for (int i = 0; i + 12 <= n; i += 4)
        for (int j = 0; j < nm; j++)
            for (int w = 0; w < 2; w++) {
                const float *v = m[j] + 12 * w;
                if (close1(d[i], v[0]) && close1(d[i + 1], v[1]) && close1(d[i + 2], v[2]) && close1(d[i + 3], v[3]) &&
                    close1(d[i + 4], v[4]) && close1(d[i + 8], v[8])) {
                    for (int r = i / 4; r < i / 4 + 3 && r < 256; r++) rows[r / 64] |= 1ull << (r % 64);
                    any = true;
                }
            }
    for (int i = 0; i + 3 <= n; i += 4)   // (the eye's place: patched in the right pass, not a reason to mark)
        for (int j = 0; j < nm; j++)
            if (close1(d[i], e[j][0]) && close1(d[i + 1], e[j][1]) && close1(d[i + 2], e[j][2])) {
                any = true;
            }
    return any;
}

// the pass's patch: the left view (as the game has it: searched for), and what goes in its place
static struct {
    bool on;
    float vl[12], vr[12];        // view, row-major 3x4
    float il[12], ir[12];        // inverse view (rotation transposed, the eye's place)
    float el[3], er[3];          // the eye's place
    float t0[4], t1[4];
    float d[16], di[16];         // left view space -> right view space (V_R V_L^-1), and back
    uint64_t buffers, patched, n_v, n_vp, n_p, n_iv, n_eye, n_ctx;
    float sx, sy;                // the projection's offset per unit of field centre (tan / half-width)
} rp;

static void mul44(const float *a, const float *b, float *o) {   // row-major 4x4: o = a b
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            o[4 * i + j] = a[4 * i] * b[j] + a[4 * i + 1] * b[4 + j] + a[4 * i + 2] * b[8 + j] + a[4 * i + 3] * b[12 + j];
}

static void inv_view(const float *v, float *o) {
    for (int i = 0; i < 3; i++) {
        o[4 * i] = v[i], o[4 * i + 1] = v[4 + i], o[4 * i + 2] = v[8 + i];
        o[4 * i + 3] = -(v[i] * v[3] + v[4 + i] * v[7] + v[8 + i] * v[11]);
    }
}

bool vr_sync_right_begin(uint64_t pair_id) {
    SyncFrame s;
    bool ok = false;
    pthread_mutex_lock(&frames_lock);
    for (int i = 0; i < SYNC_FRAMES; i++)
        if (frames[i].id == pair_id && pair_id) s = frames[i], ok = true;
    pthread_mutex_unlock(&frames_lock);
    if (!ok) return false;
    vr_sync_lookat_matrix(s.f0, rp.vl);
    vr_sync_lookat_matrix(s.f1, rp.vr);
    inv_view(rp.vl, rp.il);
    inv_view(rp.vr, rp.ir);
    memcpy(rp.el, s.f0, 12), memcpy(rp.er, s.f1, 12);
    memcpy(rp.t0, s.t0, 16), memcpy(rp.t1, s.t1, 16);
    {   // D = V_R V_L^-1 and its inverse V_L V_R^-1 (4x4, rigid)
        float vl4[16], vr4[16], il4[16], ir4[16];
        for (int i = 0; i < 12; i++) vl4[i] = rp.vl[i], vr4[i] = rp.vr[i], il4[i] = rp.il[i], ir4[i] = rp.ir[i];
        vl4[12] = vl4[13] = vl4[14] = 0, vl4[15] = 1;
        memcpy(vr4 + 12, vl4 + 12, 16), memcpy(il4 + 12, vl4 + 12, 16), memcpy(ir4 + 12, vl4 + 12, 16);
        mul44(vr4, il4, rp.d);
        mul44(vl4, ir4, rp.di);
    }
    rp.on = true;
    return true;
}

void vr_sync_log_camera(void) {   // (exec.c's dump: the latest frame's left view)
    pthread_mutex_lock(&frames_lock);
    const SyncFrame *f = &frames[(frames_next + SYNC_FRAMES - 1) % SYNC_FRAMES];
    for (int r = 0; r < 3; r++)
        LOG("[vr-dump] view row %d %.7g %.7g %.7g %.7g\n", r, f->vl[4 * r], f->vl[4 * r + 1], f->vl[4 * r + 2], f->vl[4 * r + 3]);
    pthread_mutex_unlock(&frames_lock);
}

void vr_sync_right_end(void) {
    rp.on = false;
    static uint64_t said;
    uint64_t now = plat_now_ns();
    if (now - said > 4000000000ull) {
        said = now;
        LOG("[vr-sync] right pass: %llu of %llu constant buffers patched (view %llu, view-projection %llu, projection %llu, "
            "inverse view %llu, eye %llu, context blocks with the last frame's camera and the shadow cascades %llu); "
            "projection offset scale %.3f %.3f\n", (unsigned long long)rp.patched,
            (unsigned long long)rp.buffers, (unsigned long long)rp.n_v, (unsigned long long)rp.n_vp,
            (unsigned long long)rp.n_p, (unsigned long long)rp.n_iv, (unsigned long long)rp.n_eye,
            (unsigned long long)rp.n_ctx, rp.sx, rp.sy);
        rp.buffers = rp.patched = rp.n_v = rp.n_vp = rp.n_p = rp.n_iv = rp.n_eye = rp.n_ctx = 0;
    }
}

static bool match(const float *d, const float *m, int n) {
    for (int i = 0; i < n; i++)
        if (!close1(d[i], m[i])) return false;
    return true;
}

// the right eye's projection from the left one's (row-major 4x4): its own field's scale and centre
static void right_proj(const float *pl, float *pr) {
    memcpy(pr, pl, 64);
    const float *a = rp.t0, *b = rp.t1;
    pr[0] = pl[0] * a[0] / b[0];
    pr[5] = pl[5] * a[1] / b[1];
    float cl = a[2] / a[0], cr = b[2] / b[0], ul = a[3] / a[1], ur = b[3] / b[1];
    // the offset per unit of centre, from the left projection itself (its jitter, a pixel's worth, is small beside it)
    float sx = fabsf(cl) > 0.02f ? pl[2] / cl : 1, sy = fabsf(ul) > 0.02f ? pl[6] / ul : 1;
    if (!(fabsf(sx) > 0.25f && fabsf(sx) < 4)) sx = 1;
    if (!(fabsf(sy) > 0.25f && fabsf(sy) < 4)) sy = 1;
    rp.sx = sx, rp.sy = sy;
    pr[2] = pl[2] + sx * (cr - cl);
    pr[6] = pl[6] + sy * (ur - ul);
}

static void mul_pv(const float *p, const float *v, float *o) {   // p 4x4 * [v; 0 0 0 1]
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            o[4 * i + j] = p[4 * i] * v[j] + p[4 * i + 1] * v[4 + j] + p[4 * i + 2] * v[8 + j] + (j == 3 ? p[4 * i + 3] : 0);
}

// exec.c cbuf_info, in the right eye's pass: a constant buffer's bytes with the camera's matrices put for the right eye
// into dst; false when it has none (the caller uses its usual copy)
bool vr_sync_patch(const void *src, uint64_t size, void *dst) {
    if (!rp.on) return false;
    rp.buffers++;
    const float *d = src;
    int n = (int)((size < 0x400 ? size : 0x400) / 4);   // (the census found the camera's blocks within the first 0x310 bytes)
    bool any = false;
    float *o = dst;
    for (int i = 0; i + 12 <= n; i += 4) {
        if (match(d + i, rp.vl, 12)) {
            if (!any) memcpy(dst, src, size), any = true;
            memcpy(o + i, rp.vr, 48), rp.n_v++;
            // view-projection after it: its last row minus the view's third
            if (i + 28 <= n && match(d + i + 24, (float[]){-rp.vl[8], -rp.vl[9], -rp.vl[10], -rp.vl[11]}, 4) &&
                i + 44 <= n && d[i + 40] == 0 && d[i + 41] == 0 && d[i + 42] == -1 && d[i + 43] == 0) {
                float pr[16];
                right_proj(d + i + 28, pr);
                memcpy(o + i + 28, pr, 64), rp.n_p++;
                mul_pv(pr, rp.vr, o + i + 12), rp.n_vp++;
                // The context block (the scene's cbuf 3): the inverse at +0xb0, then the last frame's camera (rows 21-34:
                // view, view-projection, projection, inverse - TAA's and the motion vectors') and the sun's shadow
                // cascades (rows 42-53: three 4x4 from view space, S V^-1, read by the shadow pass at 42 + 4 x cascade).
                // Both go to the right eye's view space: the last view D V, the cascades M D^-1
                if (i + 54 * 4 <= n && match(d + i + 44, rp.il, 12)) {
                    const float *vp = d + i + 84;   // (row 21)
                    float v4[16], dv[16], pp[16];
                    memcpy(v4, vp, 48), v4[12] = v4[13] = v4[14] = 0, v4[15] = 1;
                    mul44(rp.d, v4, dv);
                    memcpy(o + i + 84, dv, 48);
                    right_proj(d + i + 112, pp);   // (row 28)
                    memcpy(o + i + 112, pp, 64);
                    mul_pv(pp, dv, o + i + 96);    // (row 24)
                    float iv4[16], ivr[16];
                    memcpy(iv4, d + i + 128, 48), iv4[12] = iv4[13] = iv4[14] = 0, iv4[15] = 1;   // (row 32)
                    mul44(iv4, rp.di, ivr);
                    memcpy(o + i + 128, ivr, 48);
                    for (int c = 0; c < 3; c++) {   // (rows 42, 46, 50)
                        float mr[16];
                        mul44(d + i + 168 + 16 * c, rp.di, mr);
                        memcpy(o + i + 168 + 16 * c, mr, 64);
                    }
                    rp.n_ctx++;
                }
            }
            i += 8;
            continue;
        }
        if (match(d + i, rp.il, 12)) {
            if (!any) memcpy(dst, src, size), any = true;
            memcpy(o + i, rp.ir, 48), rp.n_iv++;
            i += 8;
            continue;
        }
    }
    for (int i = 0; i + 3 <= n; i += 4)
        if (match(d + i, rp.el, 3)) {
            if (!any) memcpy(dst, src, size), any = true;
            memcpy(o + i, rp.er, 12), rp.n_eye++;
        }
    if (any) rp.patched++;
    return any;
}
