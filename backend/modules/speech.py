"""Model 1 - Speech / Voice Analysis.  Input: word timestamps from Whisper  ->  delivery score.

Measures what can be read straight from the recording's word timings:
  pace (words per minute), filler words, and long pauses between words.
Pitch / tone is NOT measured. If the answer was typed (no audio), the module returns None
and is left out of the fusion instead of reporting an invented number.
"""

import re

from .base import ModuleResult

MODULE_INFO = {
    "id": "speech",
    "name": "Speech Analysis",
    "role": "scorer",
    "inputs": ["word timestamps (faster-whisper)"],
    "status": "live",
    "measures": "pace (WPM), filler words, long pauses",
    "planned_stack": "add pitch variance with librosa",
}

LONG_PAUSE_SEC = 1.5       # a gap this long between two words counts as a pause
IDEAL_WPM = (120, 165)     # comfortable interview pace; outside this range is penalised
MIN_WORDS = 15             # below this, pace is too noisy to trust

# Sounds that are always fillers.
SOUND_FILLERS = {"um", "umm", "uh", "uhh", "er", "erm", "hmm", "mm", "mmm"}
# Words that are fillers in interviews, counted wherever they appear.
WORD_FILLERS = {"basically", "actually", "literally"}
# Two-word fillers.
PHRASE_FILLERS = {("you", "know"), ("i", "mean"), ("sort", "of"), ("kind", "of")}


def _norm(word: str) -> str:
    return re.sub(r"[^a-z']", "", word.lower())


def count_fillers(words: list) -> dict:
    """words: [{"word", "start", "end"}]. Returns {"total": n, "by_word": {filler: count}}.

    "like" is only counted when it is set off by a comma, because "I like Python" is not a filler.
    """
    raw = [w["word"] for w in words]
    toks = [_norm(w) for w in raw]
    found, i = {}, 0
    while i < len(toks):
        t = toks[i]
        hit = None
        if i + 1 < len(toks) and (t, toks[i + 1]) in PHRASE_FILLERS:
            hit, step = f"{t} {toks[i + 1]}", 2
        elif t in SOUND_FILLERS or t in WORD_FILLERS:
            hit, step = t, 1
        elif t == "like" and (raw[i].rstrip().endswith(",") or (i > 0 and raw[i - 1].rstrip().endswith(","))):
            hit, step = "like", 1
        else:
            step = 1
        if hit:
            found[hit] = found.get(hit, 0) + 1
        i += step
    return {"total": sum(found.values()), "by_word": found}


def metrics_from_words(words: list) -> dict:
    n = len(words)
    span = max(words[-1]["end"] - words[0]["start"], 0.0)
    wpm = round(n / span * 60) if span >= 2.0 else None
    gaps = [max(words[i]["start"] - words[i - 1]["end"], 0.0) for i in range(1, n)]
    long_gaps = [g for g in gaps if g >= LONG_PAUSE_SEC]
    fillers = count_fillers(words)
    return {
        "word_count": n,
        "speaking_seconds": round(span, 1),
        "wpm": wpm,
        "filler_words": fillers["total"],
        "filler_per_100_words": round(fillers["total"] / n * 100, 1) if n else 0.0,
        "filler_breakdown": fillers["by_word"],
        "long_pauses": len(long_gaps),
        "longest_pause_sec": round(max(gaps), 1) if gaps else 0.0,
    }


def score_from_metrics(m: dict) -> float:
    """Transparent rubric, 100 points: pace, fillers, pauses."""
    score = 100.0
    wpm = m["wpm"]
    if wpm is not None:
        lo, hi = IDEAL_WPM
        if wpm < lo:
            score -= (lo - wpm) * 0.6
        elif wpm > hi:
            score -= (wpm - hi) * 0.6
    score -= min(m["filler_per_100_words"], 15) * 2.5
    score -= min(m["long_pauses"], 8) * 3.0
    return max(0.0, min(100.0, score))


def analyze(session: dict) -> ModuleResult | None:
    words = session.get("words")
    if not words or len(words) < 3:
        return None  # typed answer or empty recording: nothing to measure

    m = metrics_from_words(words)
    notes = []
    wpm = m["wpm"]
    if m["word_count"] < MIN_WORDS or wpm is None:
        notes.append(f"Only {m['word_count']} spoken words, too short to judge your pace reliably.")
    elif wpm > IDEAL_WPM[1]:
        notes.append(f"You spoke at {wpm} WPM, which is fast. Aim for about 140.")
    elif wpm < IDEAL_WPM[0]:
        notes.append(f"You spoke at {wpm} WPM, which is slow. A slightly brisker pace sounds more confident.")
    else:
        notes.append(f"Good speaking pace ({wpm} WPM).")
    if m["filler_words"]:
        top = sorted(m["filler_breakdown"].items(), key=lambda kv: -kv[1])[:3]
        listed = ", ".join(f'"{k}" x{v}' for k, v in top)
        notes.append(f"{m['filler_words']} filler words ({listed}). Pause silently instead.")
    if m["long_pauses"]:
        notes.append(f"{m['long_pauses']} long pauses (longest {m['longest_pause_sec']} s). Short pauses to think are fine.")

    return ModuleResult(
        module_id="speech", name=MODULE_INFO["name"], score=score_from_metrics(m),
        status=MODULE_INFO["status"], metrics=m, notes=notes,
    )
