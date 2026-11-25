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

// rt_lookat (vr_camera_lookat), before the game recomputes the view: the matrix there is the one it computed last time
void vr_sync_note_camera(const float *f) {
    if (!census_on()) return;
    const float *m = (const float *)((const char *)f - 0x38 + 0x8);
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
