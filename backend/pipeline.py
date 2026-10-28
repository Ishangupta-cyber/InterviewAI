"""The orchestrator - this file IS the architecture diagram, in code.

    capture -> preprocess -> 5 scorers (parallel, independent)
            -> fusion (hub) -> bias guard -> report
                            -> interviewer agent picks the next question

Read this file top to bottom and you can explain the whole system to a panel.
"""

import time

import registry
from modules import fusion, bias_guard, interviewer_agent


def preprocess(raw: dict) -> dict:
    """Normalise whatever the browser sent into the single session dict that
    every module receives. Real version: extract audio from the video blob,
    run speech-to-text, sample frames at N fps."""
    # Transcription happens earlier (POST /api/transcribe/ -> faster-whisper); the browser sends the
    # word timestamps and a camera summary (MediaPipe runs in the browser, so no video is uploaded).
    return {
        "session_id": raw["session_id"],
        "question": raw.get("question", ""),
        "transcript": raw.get("transcript", ""),
        "words": raw.get("words"),       # [{"word", "start", "end"}] or None for a typed answer
        "vision": raw.get("vision"),     # camera summary or None when the camera was off
        "duration_sec": raw.get("duration_sec", 0),
    }


def run(raw: dict) -> dict:
    """Full single-answer analysis. Returns everything the report page needs."""
    started = time.time()
    session = preprocess(raw)

    # --- the 5 spokes: independent, order does not matter -------------------
    # TODO(real): these become genuinely parallel (ThreadPool / async) once the
    # models are heavy. Today they are fast enough to run in sequence.
    # A scorer is left out when it is still a stub (it would return invented numbers) or when it has
    # nothing to measure (typed answer, camera off). The fusion re-balances over what remains.
    results = []
    for module in registry.SCORERS:
        if module.MODULE_INFO["status"] == "stub":
            continue
        result = module.analyze(session)
        if result is not None:
            results.append(result)

    # --- the hub: the only place modalities are combined --------------------
    fused = fusion.fuse(results)

    # --- the guard: last stop before the candidate sees anything ------------
    guard = bias_guard.check(fused, session)

    return {
        "session_id": session["session_id"],
        "question": session["question"],
        "transcript": session["transcript"],
        "modules": [r.to_dict() for r in results],
        "fusion": fused,
        "guard": guard,
        "elapsed_ms": int((time.time() - started) * 1000),
    }


def next_question(pending, last_fusion, last_question="", last_transcript="", last_was_probe=False):
    """Thin pass-through so views never import the agent directly - keeps the
    pipeline the single entry point into the model layer."""
    return interviewer_agent.next_question(pending, last_fusion, last_question,
                                           last_transcript, last_was_probe)
