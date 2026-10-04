"""Model 5 - Eye Contact / Gaze Tracking.  Input: video frames -> focus score."""

from .base import ModuleResult, seeded_random

MODULE_INFO = {
    "id": "eye_gaze",
    "name": "Eye Contact",
    "role": "scorer",
    "inputs": ["video"],
    "status": "stub",
    "measures": "percent time on camera, look-away count, blink rate",
    "planned_stack": "MediaPipe Iris + head-pose estimation (solvePnP)",
}


def analyze(session: dict) -> ModuleResult:
    # TODO(real): per frame estimate iris centre + head yaw/pitch; a frame counts
    # as "on camera" when the gaze vector falls inside a cone around the lens.
    rng = seeded_random(session["session_id"], "eye_gaze")

    contact_pct = rng.randint(35, 95)
    look_aways = rng.randint(1, 20)
    blink_rate = rng.randint(8, 32)

    score = contact_pct * 0.9 - look_aways * 1.2
    if blink_rate > 26:
        score -= 6
    score = max(0.0, min(100.0, score))

    notes = ["Eye contact held " + str(contact_pct) + "% of the answer."]
    if contact_pct < 60:
        notes.append("Look at the camera lens, not your own video preview.")
    if look_aways > 12:
        notes.append(str(look_aways) + " look-aways - glance away only while thinking.")

    return ModuleResult(
        module_id="eye_gaze", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"eye_contact_pct": contact_pct, "look_aways": look_aways,
                 "blink_rate": blink_rate},
        notes=notes,
    )
