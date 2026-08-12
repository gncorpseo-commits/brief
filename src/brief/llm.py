from __future__ import annotations

import json
import re
from typing import Any

import httpx

from brief.config import OLLAMA_HOST, OLLAMA_MODEL


class LLMError(RuntimeError):
    pass


def ollama_available(timeout: float = 1.5) -> bool:
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Call Ollama chat and parse a JSON object from the response."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        r = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=180.0)
        r.raise_for_status()
    except Exception as e:
        raise LLMError(f"Ollama 호출 실패: {e}") from e
    content = r.json().get("message", {}).get("content", "")
    return parse_json_object(content)


def chat_text(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.4,
) -> str:
    payload = {
        "model": model or OLLAMA_MODEL,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    try:
        r = httpx.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=180.0)
        r.raise_for_status()
    except Exception as e:
        raise LLMError(f"Ollama 호출 실패: {e}") from e
    return (r.json().get("message", {}).get("content") or "").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise LLMError("JSON 객체를 찾지 못했습니다")
    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise LLMError("JSON 루트가 object가 아닙니다")
    return data
