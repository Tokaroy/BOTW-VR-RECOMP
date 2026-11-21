// An arrow leaving the bow (tools/patches.py _arrow_aim, main+0x931590): the shoot step of its AI has just made the
// way it flies (a unit vector, from where the arrow is to the shooter's aim point) and is about to scale it by the
// first speed; the aim point (target) goes to the arrow as its TargetPos (docs/vr/re-notes.md). The VR mode (make
// VR=1) turns both along the player's hands; otherwise nothing happens.
#ifdef SW_VR
void vr_arrow_aim(float *dir, const float *origin, float *target);
#endif

// A lifted object thrown (tools/patches.py _grab_throw, main+0xc76e20): vel is the throw velocity the game just made
// (world, m/s), about to go to the object. The VR mode puts the hand's own throw there.
#ifdef SW_VR
void vr_grab_throw(float *vel);
#endif
void rt_grab_throw(float *vel) {
#ifdef SW_VR
    vr_grab_throw(vel);
#else
    (void)vel;
#endif
}

void rt_arrow_aim(float *dir, const float *origin, float *target) {
#ifdef SW_VR
    vr_arrow_aim(dir, origin, target);
#else
    (void)dir, (void)origin, (void)target;
#endif
}
