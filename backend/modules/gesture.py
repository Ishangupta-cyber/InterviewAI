"""Model 4 - Gesture / Posture Analysis.  Input: video frames -> body language."""

from .base import ModuleResult, seeded_random

MODULE_INFO = {
    "id": "gesture",
    "name": "Gesture & Posture",
    "role": "scorer",
    "inputs": ["video"],
    "status": "stub",
    "measures": "posture stability, hand movement rate, fidgeting",
    "planned_stack": "MediaPipe Pose (33 landmarks) + rule-based heuristics",
}


def analyze(session: dict) -> ModuleResult:
    # TODO(real): pose estimation per frame; shoulder-line tilt for slouch,
    # wrist velocity for gesture rate, high-frequency jitter for fidgeting.
    rng = seeded_random(session["session_id"], "gesture")

    posture = rng.randint(50, 98)
    gesture_rate = rng.randint(2, 30)
    fidget = rng.randint(0, 14)

    score = posture * 0.6
    score += (25 - abs(gesture_rate - 14)) * 1.2
    score -= fidget * 1.8
    score = max(0.0, min(100.0, score))

    notes = []
    if posture < 65:
        notes.append("Posture drifted - sit back and keep shoulders level.")
    if gesture_rate < 5:
        notes.append("Almost no hand gestures; a few look more natural.")
    elif gesture_rate > 24:
        notes.append("Very busy hands - it pulls focus from your answer.")
    if fidget > 8:
        notes.append("Noticeable fidgeting detected.")
    if not notes:
        notes.append("Steady posture and natural gestures.")

    return ModuleResult(
        module_id="gesture", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"posture_stability": posture, "gestures_per_min": gesture_rate,
                 "fidget_events": fidget},
        notes=notes,
    )
