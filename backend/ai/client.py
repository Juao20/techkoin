"""Single entry point to the language model (spec 10.1).

`complete()` calls Groq in JSON mode, validates the answer with a pydantic schema, retries once
when the JSON is invalid, and otherwise returns the feature's deterministic fallback. Without
GROQ_API_KEY the application runs entirely on fallbacks.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from django.conf import settings
from pydantic import BaseModel, ValidationError

from . import privacy, prompts
from .models import AIRequestLog

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1"
SYSTEM = (
    "Tu es l'assistant de TechKoin, une place de marché d'appareils au Bénin. "
    "Réponds uniquement en JSON valide, en français, sans emoji."
)


@dataclass
class Result:
    value: BaseModel
    fallback_used: bool
    model: str = ""


def http_client(timeout: float) -> httpx.Client:
    """Overridable in tests."""
    return httpx.Client(timeout=timeout)


def has_key() -> bool:
    return bool(settings.GROQ_API_KEY)


def model_name(kind: str) -> str:
    return settings.GROQ_MODEL_FAST if kind == "fast" else settings.GROQ_MODEL_SMART


def _log(feature, user, shop, **fields):
    try:
        AIRequestLog.objects.create(feature=feature, user=user, shop=shop, **fields)
    except Exception:  # logging must never break a feature
        logger.exception("AIRequestLog failed")


def _post_json(messages, model: str, timeout: float) -> tuple[dict, int, int]:
    with http_client(timeout) as client:
        response = client.post(
            f"{GROQ_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
        )
    response.raise_for_status()
    body = response.json()
    usage = body.get("usage", {})
    content = body["choices"][0]["message"]["content"]
    return json.loads(content), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def complete[T: BaseModel](
    feature: str,
    prompt_name: str,
    variables: dict,
    schema: type[T],
    model: str = "smart",
    *,
    fallback: Callable[[], T],
    user=None,
    shop=None,
    timeout: float | None = None,
    validate: Callable[[T], None] | None = None,
) -> Result:
    """Ask the model, or return `fallback()` when it cannot answer usefully.

    `validate` may raise ValueError to reject a well-formed but wrong answer (for example a
    winner that is not among the compared listings): the fallback is used instead.
    """
    version, prompt = prompts.render(prompt_name, variables)
    name = model_name(model)
    started = time.monotonic()
    base = dict(model=name, prompt_version=version)

    def use_fallback(error: str, **extra):
        _log(
            feature,
            user,
            shop,
            success=False if error and error != "no_key" else True,
            fallback_used=True,
            error=error[:300],
            latency_ms=int((time.monotonic() - started) * 1000),
            **base,
            **extra,
        )
        return Result(fallback(), True, name)

    if not has_key():
        return use_fallback("no_key")

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    try:
        privacy.check(messages)
    except privacy.PersonalDataError as exc:
        return use_fallback(f"privacy: {exc}")

    limit = timeout or settings.AI_TIMEOUT_SECONDS
    input_tokens = output_tokens = 0
    last_error = "invalid_json"
    for _ in range(2):  # one retry when the JSON is invalid
        try:
            data, tin, tout = _post_json(messages, name, limit)
            input_tokens += tin
            output_tokens += tout
            value = schema.model_validate(data)
            if validate:
                validate(value)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return use_fallback(f"network: {type(exc).__name__}")
        except httpx.HTTPStatusError as exc:
            return use_fallback(f"http_{exc.response.status_code}")
        except (json.JSONDecodeError, ValidationError, KeyError, IndexError, ValueError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"[:200]
            continue
        _log(
            feature,
            user,
            shop,
            success=True,
            fallback_used=False,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=int((time.monotonic() - started) * 1000),
            **base,
        )
        return Result(value, False, name)
    return use_fallback(last_error, input_tokens=input_tokens, output_tokens=output_tokens)


def _post_chat(messages, model: str, timeout: float, tools: list[dict]) -> tuple[dict, int, int]:
    with http_client(timeout) as client:
        response = client.post(
            f"{GROQ_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.1,
            },
        )
    response.raise_for_status()
    body = response.json()
    usage = body.get("usage", {})
    return (
        body["choices"][0]["message"],
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


def chat_with_tools(
    feature: str,
    system: str,
    question: str,
    tools: list[dict],
    run_tool: Callable[[str, dict], dict],
    *,
    user=None,
    shop=None,
    max_rounds: int = 4,
    timeout: float | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]] | None:
    """Let the model call predefined functions (never SQL) and answer from their results.

    `run_tool(name, arguments)` executes a function that is already restricted to the signed-in
    shop. Returns (answer, calls) with calls = [{name, arguments, result}], or None when the model
    is unavailable, so that the caller can fall back to a deterministic answer.
    """
    if not has_key():
        _log(feature, user, shop, success=True, fallback_used=True, error="no_key")
        return None
    started = time.monotonic()
    name = model_name("smart")
    messages = [{"role": "system", "content": system}, *(history or [])]
    messages.append({"role": "user", "content": question})
    calls: list[dict] = []
    tokens_in = tokens_out = 0

    def fail(error: str):
        _log(
            feature,
            user,
            shop,
            model=name,
            success=False,
            fallback_used=True,
            error=error[:300],
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        return None

    try:
        for _ in range(max_rounds):
            privacy.check(messages)
            message, tin, tout = _post_chat(
                messages, name, timeout or settings.AI_TIMEOUT_SECONDS, tools
            )
            tokens_in += tin
            tokens_out += tout
            requested = message.get("tool_calls") or []
            if not requested:
                answer = (message.get("content") or "").strip()
                if not answer:
                    return fail("empty_answer")
                _log(
                    feature,
                    user,
                    shop,
                    model=name,
                    success=True,
                    fallback_used=False,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
                return answer, calls
            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": requested,
                }
            )
            for call in requested:
                fn = call["function"]
                try:
                    arguments = json.loads(fn.get("arguments") or "{}")
                    result = run_tool(fn["name"], arguments)
                except (ValueError, TypeError, KeyError) as exc:
                    arguments, result = {}, {"error": f"appel invalide : {exc}"}
                calls.append({"name": fn["name"], "arguments": arguments, "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
        return fail("too_many_rounds")
    except privacy.PersonalDataError as exc:
        return fail(f"privacy: {exc}")
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        return fail(f"network: {type(exc).__name__}")
    except httpx.HTTPStatusError as exc:
        return fail(f"http_{exc.response.status_code}")
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
        return fail(f"{type(exc).__name__}: {exc}")


def transcribe(audio: bytes, filename: str, content_type: str, user=None) -> str | None:
    """Speech to text with Whisper. Returns None when unavailable; the audio is never stored."""
    started = time.monotonic()
    if not has_key():
        _log("voice_stt", user, None, success=True, fallback_used=True, error="no_key")
        return None
    try:
        with http_client(settings.AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{GROQ_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                data={"model": settings.GROQ_MODEL_STT, "language": "fr"},
                files={"file": (filename, audio, content_type)},
            )
        response.raise_for_status()
        text = response.json().get("text", "").strip()
    except (httpx.HTTPError, ValueError) as exc:
        _log(
            "voice_stt",
            user,
            None,
            success=False,
            fallback_used=True,
            error=type(exc).__name__,
            latency_ms=int((time.monotonic() - started) * 1000),
        )
        return None
    _log(
        "voice_stt",
        user,
        None,
        model=settings.GROQ_MODEL_STT,
        success=True,
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    return text or None
