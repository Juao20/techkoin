"""F3: voice publication. Speech to text, then structured extraction that pre-fills the form."""

from __future__ import annotations

from catalog.search import find_models

from . import client, privacy
from .fallback import voice_parser
from .schemas import VoiceFields
from .search import _model_tokens

MAX_BYTES = 3 * 1024 * 1024  # about 60 s of compressed speech
MAX_SECONDS = 60


def run(audio: bytes, filename: str, content_type: str, user=None) -> dict:
    """The audio lives in memory only for the duration of this call."""
    transcript = client.transcribe(audio, filename, content_type, user=user)
    del audio
    if transcript is None:
        return {"available": False, "used_ai": False}

    tokens = _model_tokens()

    def fallback() -> VoiceFields:
        return voice_parser.parse(transcript, known_terms=lambda w: w in tokens)

    result = client.complete(
        "voice_extract",
        "voice",
        {"transcript": privacy.scrub_text(transcript)},
        VoiceFields,
        "fast",
        fallback=fallback,
        user=user,
    )
    fields = result.value
    device = None
    if fields.model_text:
        found = find_models(fields.model_text, fields.category)
        if found:
            m = found[0]
            device = {"slug": m.slug, "label": str(m), "category": m.category}
    return {
        "available": True,
        "transcript": transcript,
        "fields": fields.model_dump(),
        "device_model": device,
        "used_ai": not result.fallback_used,
    }
