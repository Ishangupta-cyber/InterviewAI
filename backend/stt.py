"""Speech-to-text with faster-whisper (Module 4).

The model loads lazily on the first request (it downloads once, then is cached),
so `runserver` starts instantly. CPU + int8 keeps it usable without a GPU.
Word timestamps are returned too; the speech scorer will use them for pace and pauses.
"""

import threading

from django.conf import settings

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
        return _model


def transcribe(path: str) -> dict:
    """Returns {"text", "duration", "words": [{"word", "start", "end"}]}."""
    segments, info = _get_model().transcribe(
        path, language="en", vad_filter=True, word_timestamps=True, beam_size=1)
    text_parts, words = [], []
    for seg in segments:
        text_parts.append(seg.text.strip())
        for w in seg.words or []:
            words.append({"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)})
    return {"text": " ".join(text_parts).strip(), "duration": round(info.duration, 1), "words": words}
