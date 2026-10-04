"""Model 1 - Speech / Voice Analysis.  Input: audio  ->  fluency score."""

from .base import ModuleResult, seeded_random

MODULE_INFO = {
    "id": "speech",
    "name": "Speech Analysis",
    "role": "scorer",
    "inputs": ["audio"],
    "status": "stub",
    "measures": "pace (WPM), pause length, pitch variance, filler words",
    "planned_stack": "librosa + webrtcvad (or Whisper timestamps for fillers)",
}


def analyze(session: dict) -> ModuleResult:
    # TODO(real): load session["audio_path"], compute WPM from word timestamps,
    # detect pauses with a VAD, get pitch variance via librosa.yin().
    rng = seeded_random(session["session_id"], "speech")

    wpm = rng.randint(105, 175)
    fillers = rng.randint(0, 9)
    long_pauses = rng.randint(0, 5)
    pitch_var = round(rng.uniform(0.2, 0.9), 2)

    # simple transparent scoring so the demo is explainable
    score = 100.0
    score -= abs(wpm - 140) * 0.35
    score -= fillers * 3.0
    score -= long_pauses * 2.5
    score = max(0.0, min(100.0, score))

    notes = []
    if wpm > 160:
        notes.append("You spoke at " + str(wpm) + " WPM - slow down, aim for ~140.")
    elif wpm < 115:
        notes.append("You spoke at " + str(wpm) + " WPM - a brisker pace sounds more confident.")
    else:
        notes.append("Good speaking pace (" + str(wpm) + " WPM).")
    if fillers > 4:
        notes.append(str(fillers) + " filler words detected - pause silently instead.")

    return ModuleResult(
        module_id="speech", name=MODULE_INFO["name"], score=score,
        status=MODULE_INFO["status"],
        metrics={"wpm": wpm, "filler_words": fillers,
                 "long_pauses": long_pauses, "pitch_variance": pitch_var},
        notes=notes,
    )
