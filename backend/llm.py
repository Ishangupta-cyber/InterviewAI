"""Thin Gemini wrapper. Every caller must handle None (no key / API error) and
fall back to an offline heuristic, so the demo never hard-fails on the network."""

import json
import logging

from django.conf import settings

log = logging.getLogger(__name__)


def available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def generate_json(prompt: str):
    """Ask Gemini for a JSON answer. Returns the parsed object, or None on any failure."""
    if not available():
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(resp.text)
    except Exception as exc:  # network, quota, bad JSON - all mean "use the fallback"
        log.warning("Gemini call failed: %s", exc)
        return None
