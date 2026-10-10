"""Minimal OpenRouter chat client (stdlib only)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API = "https://openrouter.ai/api/v1"

# Prefer endpoints serving full or FP8 precision so scores reflect the model,
# not an aggressive server-side quantization. Overridable per model.
DEFAULT_PROVIDER = {"quantizations": ["bf16", "fp16", "fp8"], "allow_fallbacks": True}


@dataclass
class ChatResult:
    text: str = ""
    provider: str | None = None
    cost: float = 0.0
    finish_reason: str | None = None
    error: str | None = None
    usage: dict = field(default_factory=dict)


def _post(path: str, body: dict, timeout: int) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "Model Tested",
            "HTTP-Referer": "https://modeltested.com",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chat(model: dict, prompt: str, max_tokens: int = 8192, timeout: int = 600) -> ChatResult:
    body = {
        "model": model["openrouter_id"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": model.get("max_tokens", max_tokens),
        "usage": {"include": True},
        "provider": model.get("provider") or DEFAULT_PROVIDER,
    }
    if "temperature" in model:
        body["temperature"] = model["temperature"]
    if "reasoning" in model:
        body["reasoning"] = model["reasoning"]

    last_err = None
    for attempt in range(4):
        try:
            d = _post("/chat/completions", body, timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            last_err = f"HTTP {e.code}: {detail}"
            if e.code == 404 and "provider" in body and model.get("provider") is None:
                # No endpoint matches the precision filter: fall back to any provider.
                body.pop("provider")
                continue
            if e.code in (408, 429, 500, 502, 503, 504):
                time.sleep(5 * 2 ** attempt)
                continue
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = f"network: {e}"
            time.sleep(5 * 2 ** attempt)
            continue

        if "error" in d:
            last_err = f"API: {str(d['error'])[:300]}"
            time.sleep(5 * 2 ** attempt)
            continue
        choice = (d.get("choices") or [{}])[0]
        usage = d.get("usage") or {}
        return ChatResult(
            text=(choice.get("message") or {}).get("content") or "",
            provider=d.get("provider"),
            cost=float(usage.get("cost") or 0),
            finish_reason=choice.get("finish_reason"),
            usage={k: usage.get(k) for k in ("prompt_tokens", "completion_tokens")},
        )
    return ChatResult(error=last_err or "unknown error")


def list_models() -> list[dict]:
    with urllib.request.urlopen(API + "/models", timeout=60) as r:
        return json.loads(r.read())["data"]
