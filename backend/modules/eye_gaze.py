"""Model 5 - Eye Contact.  Input: per-answer camera summary (MediaPipe, computed in the browser).

"Eye contact" here means: a face is visible, the head is roughly facing the screen, and the eyes
are not turned far to a side or up. It is an attention proxy. Reading from notes or a second
monitor counts as looking away. Thresholds were set by hand and are not yet tuned on real data.
Returns None when the camera was off, so the fusion leaves this module out.
"""

from .base import ModuleResult

MODULE_INFO = {
    "id": "eye_gaze",
    "name": "Eye Contact",
    "role": "scorer",
    "inputs": ["camera summary (face landmarks, head pose, eye blendshapes)"],
    "status": "live",
    "measures": "share of the answer spent facing the screen, look-away episodes",
    "planned_stack": "MediaPipe FaceLandmarker (runs in the browser; video never uploaded)",
}

IDEAL_CONTACT_PCT = 70.0   # looking at the screen about 70% of the time reads as natural
MIN_FRAMES = 5


def clean_vision(v) -> dict | None:
    """Validate the browser's summary; returns None if it is unusable."""
    if not isinstance(v, dict):
        return None
    try:
        out = {
            "frames": int(v["frames"]),
            "face_present_pct": float(v["face_present_pct"]),
            "eye_contact_pct": float(v["eye_contact_pct"]),
            "smile_pct": float(v.get("smile_pct", 0)),
            "head_motion": float(v.get("head_motion", 0)),
            "look_away_events": int(v.get("look_away_events", 0)),
        }
    except (KeyError, TypeError, ValueError):
        return None
    if out["frames"] < MIN_FRAMES:
        return None
    for k in ("face_present_pct", "eye_contact_pct", "smile_pct"):
        out[k] = max(0.0, min(100.0, out[k]))
    out["head_motion"] = max(0.0, min(90.0, out["head_motion"]))
    return out


def analyze(session: dict) -> ModuleResult | None:
    v = clean_vision(session.get("vision"))
    if v is None:
        return None

    contact = v["eye_contact_pct"]
    score = min(100.0, contact / IDEAL_CONTACT_PCT * 100.0)

    notes = [f"You faced the screen about {round(contact)}% of the answer."]
    if v["face_present_pct"] < 80:
        notes.append("Your face was out of view for part of the answer. Check lighting and camera position.")
    elif contact < 50:
        notes.append("You looked away often. Look toward the camera when you start and finish a point.")
    elif contact >= IDEAL_CONTACT_PCT:
        notes.append("Steady eye contact.")
    if v["look_away_events"] >= 3:
        notes.append(f"{v['look_away_events']} separate look-away moments of over a second.")

    return ModuleResult(
        module_id="eye_gaze", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"eye_contact_pct": round(contact, 1), "face_present_pct": round(v["face_present_pct"], 1),
                 "look_away_events": v["look_away_events"], "frames_sampled": v["frames"]},
        notes=notes,
    )
