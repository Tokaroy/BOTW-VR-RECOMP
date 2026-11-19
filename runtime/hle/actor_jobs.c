// An actor told to skip its job pushes for a while (tools/patches.py _job_push_skip, main+0x1531ffc): the count, in game
// frames, that the game asks for (2). In VR stereo (make VR=1) two game frames show one moment, one per eye, and the
// count runs out halfway through what the game meant: it is doubled there, as BetterVR does
// (patch_RND_StereoRendering_ActorJobs.asm: LinkTag and EventTag actors missed updates, shrine doors among them).
// Otherwise it is the game's.
#include <stdbool.h>
#include <stdint.h>

#ifdef SW_VR
bool vr_job_skip_doubled(void);
#endif

uint32_t rt_job_push_skip(uint32_t frames) {
#ifdef SW_VR
    if (vr_job_skip_doubled()) return frames * 2;
#endif
    return frames;
}
