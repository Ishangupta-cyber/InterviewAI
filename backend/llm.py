"""Thin Gemini wrapper. Every caller must handle None (no key / API error) and
fall back to an offline heuristic, so the demo never hard-fails on the network."""

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)


def available() -> bool:
    return bool(settings.GEMINI_API_KEY)


ATTEMPTS = 3  # the model occasionally returns malformed JSON; a retry almost always fixes it


def generate_json(prompt: str):
    """Ask Gemini for a JSON answer. Returns the parsed object, or None if every attempt fails."""
    if not available():
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        log.warning("Gemini SDK unavailable: %s", exc)
        return None

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            resp = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt, config=config)
            return json.loads(resp.text)
        except Exception as exc:  # network, quota, bad JSON
            log.warning("Gemini call failed (attempt %d/%d): %s", attempt, ATTEMPTS, exc)
    return None
