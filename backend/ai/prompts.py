"""Prompt files live in ai/prompts/<name>.md and start with a small header:

    ---
    version: 1
    ---

Variables are written {{name}} and replaced by their JSON (or plain text) value.
"""

import re
from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"
HEADER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


@cache
def load(name: str) -> tuple[str, str]:
    """Return (version, body) of a prompt file."""
    raw = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = HEADER_RE.match(raw)
    version = "0"
    body = raw
    if match:
        body = raw[match.end() :]
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "version":
                version = value.strip()
    return version, body.strip()


def render(name: str, variables: dict) -> tuple[str, str]:
    import json

    version, body = load(name)
    for key, value in variables.items():
        text = (
            value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        )
        body = body.replace("{{" + key + "}}", text)
    return version, body
