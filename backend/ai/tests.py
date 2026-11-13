import json
from datetime import timedelta

import httpx
import pytest
from django.utils import timezone
from pydantic import BaseModel

from . import cache, client, privacy, prompts
from .models import AICache, AIRequestLog


class Answer(BaseModel):
    label: str
    score: int


def fallback():
    return Answer(label="repli", score=0)


@pytest.fixture(autouse=True)
def test_prompt(tmp_path, monkeypatch):
    (tmp_path / "ping.md").write_text("---\nversion: 3\n---\nDécris {{item}}.", encoding="utf-8")
    monkeypatch.setattr(prompts, "PROMPT_DIR", tmp_path)
    prompts.load.cache_clear()
    yield
    prompts.load.cache_clear()


@pytest.fixture
def groq(settings, monkeypatch):
    """A fake Groq server. `groq.replies` is consumed one call at a time."""
    settings.GROQ_API_KEY = "test-key"

    class Fake:
        replies: list = []
        requests: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        try:
            Fake.requests.append(json.loads(request.content))
        except ValueError:  # multipart upload
            Fake.requests.append({"multipart": True})
        reply = Fake.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(
        client, "http_client", lambda timeout: httpx.Client(transport=httpx.MockTransport(handler))
    )
    Fake.replies, Fake.requests = [], []
    return Fake


def ok(payload, tokens=(12, 7)):
    body = {
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]},
    }
    return httpx.Response(200, json=body)


def raw(content: str):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}], "usage": {}})


def call(**kw):
    return client.complete(
        "test", "ping", {"item": "un PC"}, Answer, "fast", fallback=fallback, **kw
    )


def test_without_a_key_the_fallback_answers_and_is_logged(db, settings):
    settings.GROQ_API_KEY = ""
    result = call()
    assert result.fallback_used and result.value.label == "repli"
    log = AIRequestLog.objects.get()
    assert log.fallback_used and log.success and log.error == "no_key"
    assert log.prompt_version == "3"


def test_a_valid_answer_is_used_and_logged_with_tokens(db, groq):
    groq.replies = [ok({"label": "ok", "score": 9})]
    result = call()
    assert not result.fallback_used and result.value == Answer(label="ok", score=9)
    sent = groq.requests[0]
    assert sent["model"] == "llama-3.1-8b-instant"
    assert sent["response_format"] == {"type": "json_object"}
    assert "Décris un PC." in sent["messages"][1]["content"]
    log = AIRequestLog.objects.get()
    assert (log.input_tokens, log.output_tokens, log.fallback_used) == (12, 7, False)


def test_invalid_json_is_retried_once(db, groq):
    groq.replies = [raw("pas du json"), ok({"label": "ok", "score": 1})]
    result = call()
    assert not result.fallback_used
    assert len(groq.requests) == 2


def test_two_invalid_answers_fall_back(db, groq):
    groq.replies = [ok({"label": "x"}), raw("{")]  # schema error, then broken JSON
    result = call()
    assert result.fallback_used
    log = AIRequestLog.objects.get()
    assert not log.success and log.fallback_used and log.error


def test_timeout_and_http_errors_fall_back_without_retrying(db, groq):
    groq.replies = [httpx.ReadTimeout("lent")]
    assert call().fallback_used
    groq.replies = [httpx.Response(429, json={})]
    assert call().fallback_used
    assert AIRequestLog.objects.filter(error__startswith="network").exists()
    assert AIRequestLog.objects.filter(error="http_429").exists()


def test_a_validator_can_reject_a_wrong_answer(db, groq):
    def reject(value):
        raise ValueError("gagnant inconnu")

    groq.replies = [ok({"label": "a", "score": 1}), ok({"label": "a", "score": 1})]
    result = client.complete(
        "test", "ping", {"item": "x"}, Answer, fallback=fallback, validate=reject
    )
    assert result.fallback_used


def test_personal_data_is_never_sent(db, groq):
    for item in (
        "écrire à vendeur@example.com",
        "appeler le 01 97 55 44 33",
        "IMEI 490154203237518",
    ):
        result = client.complete("test", "ping", {"item": item}, Answer, fallback=fallback)
        assert result.fallback_used
    assert groq.requests == []
    assert AIRequestLog.objects.filter(error__startswith="privacy").count() == 3


def test_privacy_check_rules():
    privacy.check({"title": "iPhone 13 128 Go", "specs": "16 Go · 512 Go SSD", "price": 185000})
    privacy.check({"text": "Prix 250 000 FCFA, batterie 86 %, 64 128 256 Go"})
    for bad in (
        {"imei": "x"},
        {"seller": {"phone": "x"}},
        {"text": "mail@example.com"},
        {"text": "+229 01 97 00 00 00"},
        {"text": "97000000"},
        {"text": "490154203237518"},
    ):
        with pytest.raises(privacy.PersonalDataError):
            privacy.check(bad)
    assert "contact retiré" in privacy.scrub_text("Appelez le 01 97 55 44 33 ou a@b.co")


def test_cache_keys_are_stable_and_expire(db):
    key = cache.make_key("search", {"q": "pc", "page": 1})
    assert key == cache.make_key("search", {"page": 1, "q": "pc"})
    assert key != cache.make_key("search", {"q": "pc", "page": 2})
    cache.put(key, "search", {"a": 1})
    assert cache.get(key) == {"a": 1}
    AICache.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert cache.get(key) is None
    assert cache.purge_expired() == 1


def test_transcription_uses_whisper_and_keeps_no_audio(db, groq):
    groq.replies = [httpx.Response(200, json={"text": "iPhone 12, 128 giga"})]
    text = client.transcribe(b"audio-bytes", "a.webm", "audio/webm")
    assert text == "iPhone 12, 128 giga"
    assert AIRequestLog.objects.get().feature == "voice_stt"
    assert not AICache.objects.exists()


def test_transcription_without_a_key_returns_none(db, settings):
    settings.GROQ_API_KEY = ""
    assert client.transcribe(b"x", "a.webm", "audio/webm") is None


def test_status_endpoint(db, client, settings):
    settings.GROQ_API_KEY = ""
    assert client.get("/api/ai/status/").json() == {
        "model_available": False,
        "voice_available": False,
    }
