"""Unit tests for the scoring modules. Run: .venv\\Scripts\\python.exe test_scoring.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["GEMINI_API_KEY"] = ""   # keep the tests offline and deterministic
import django

django.setup()

from modules import eye_gaze, facial, nlp_score, speech  # noqa: E402
import pipeline  # noqa: E402


def make_words(texts, start=0.0, step=0.4, gaps=None):
    """Evenly spaced words; gaps = {index: extra silence in seconds before that word}."""
    gaps, t, out = gaps or {}, start, []
    for i, w in enumerate(texts):
        t += gaps.get(i, 0.0)
        out.append({"word": w, "start": round(t, 2), "end": round(t + step * 0.8, 2)})
        t += step
    return out


VISION_GOOD = {"frames": 40, "face_present_pct": 98, "eye_contact_pct": 75, "smile_pct": 25,
               "head_motion": 5, "look_away_events": 1}


# ------------------------------------------------------------------ speech
def test_wpm_is_computed_from_timestamps():
    words = make_words(["word"] * 60, step=0.5)          # 60 words over ~30 s -> ~120 WPM
    m = speech.metrics_from_words(words)
    assert 115 <= m["wpm"] <= 125, m


def test_fillers_counted_correctly():
    text = "I think um the main thing is, like, caching and you know it basically helps".split()
    f = speech.count_fillers(make_words(text))
    assert f["by_word"] == {"um": 1, "like": 1, "you know": 1, "basically": 1}, f
    # "like" as a verb is NOT a filler
    g = speech.count_fillers(make_words("I like Python and I like Django".split()))
    assert g["total"] == 0, g


def test_long_pauses():
    words = make_words(["a"] * 30, gaps={10: 2.5, 20: 1.0})   # one 2.5s pause, one 1.0s (too short to count)
    m = speech.metrics_from_words(words)
    assert m["long_pauses"] == 1 and m["longest_pause_sec"] >= 2.4, m


def test_speech_score_penalises_fast_pace_and_fillers():
    calm = speech.score_from_metrics({"wpm": 140, "filler_per_100_words": 0, "long_pauses": 0})
    fast = speech.score_from_metrics({"wpm": 220, "filler_per_100_words": 0, "long_pauses": 0})
    messy = speech.score_from_metrics({"wpm": 140, "filler_per_100_words": 10, "long_pauses": 4})
    assert calm == 100 and fast < calm and messy < calm
    assert 0 <= speech.score_from_metrics({"wpm": 400, "filler_per_100_words": 99, "long_pauses": 99}) <= 100


def test_speech_none_without_audio():
    assert speech.analyze({"words": None}) is None
    assert speech.analyze({"words": make_words(["a", "b"])}) is None     # fewer than 3 words


# --------------------------------------------------------------- vision
def test_vision_validation():
    assert eye_gaze.clean_vision(None) is None
    assert eye_gaze.clean_vision({"frames": 40}) is None                           # missing fields
    assert eye_gaze.clean_vision({**VISION_GOOD, "frames": 2}) is None             # too few frames
    c = eye_gaze.clean_vision({**VISION_GOOD, "eye_contact_pct": 500, "head_motion": -3})
    assert c["eye_contact_pct"] == 100 and c["head_motion"] == 0


def test_eye_contact_score():
    hi = eye_gaze.analyze({"vision": {**VISION_GOOD, "eye_contact_pct": 80}})
    lo = eye_gaze.analyze({"vision": {**VISION_GOOD, "eye_contact_pct": 20}})
    assert hi.score == 100 and 25 <= lo.score <= 32, (hi.score, lo.score)
    assert eye_gaze.analyze({"vision": None}) is None


def test_facial_score_components():
    good = facial.analyze({"vision": VISION_GOOD})
    absent = facial.analyze({"vision": {**VISION_GOOD, "face_present_pct": 30}})
    restless = facial.analyze({"vision": {**VISION_GOOD, "head_motion": 30}})
    assert good.score > 90 and absent.score < good.score - 20 and restless.score < good.score
    assert facial.positivity_score(0) == 60 and facial.positivity_score(30) == 100 and facial.positivity_score(100) == 80


# ------------------------------------------------------------------ nlp
def test_relevance_prefers_on_topic_answers():
    q = "How do you approach debugging code that fails only in production?"
    on = "I debug production failures by reading logs and reproducing the failing code path locally."
    off = "My favourite hobby is cricket and I play every weekend with friends."
    assert nlp_score.relevance_score(q, on)[0] > nlp_score.relevance_score(q, off)[0]
    assert nlp_score.relevance_score(q, off)[0] == 0


# -------------------------------------------------------------- pipeline
def run(extra):
    return pipeline.run({"session_id": "t", "question": "Describe a project you built.",
                         "transcript": "I built a Django project and reduced load time by 40 percent as a result.",
                         **extra})


def test_pipeline_leaves_out_unmeasured_modules():
    typed = run({})
    ids = [m["module_id"] for m in typed["modules"]]
    assert ids == ["nlp_score"], ids        # no audio, no camera, gesture is a stub

    full = run({"words": make_words(("I built a Django project and reduced load time by 40 percent as a result " * 2).split()),
                "vision": VISION_GOOD})
    ids = [m["module_id"] for m in full["modules"]]
    assert ids == ["speech", "nlp_score", "facial", "eye_gaze"], ids
    assert "gesture" not in ids
    assert 0 <= full["fusion"]["overall_score"] <= 100
    weights = sum(c["weight"] for c in full["fusion"]["contributions"])
    assert abs(weights - 0.9) < 1e-9, weights   # 1.0 minus gesture's 0.10; the fusion renormalises


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            n += 1
            print("ok", name)
    print(f"{n} tests passed")
