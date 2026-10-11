"""Minimal OpenRouter chat client (stdlib only)."""
from __future__ import annotations

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

API = "https://openrouter.ai/api/v1"

# Providers whose output we can't trust. Cloudflare (Oct 2026) dropped tokens such
# as `[]` and `""` from completions, turning valid code into syntax errors.
# Answers they served are re-run (see run.py).
BLOCKED_PROVIDERS = ["Cloudflare"]

# Prefer endpoints serving full or FP8 precision so scores reflect the model,
# not an aggressive server-side quantization. Overridable per model.
DEFAULT_PROVIDER = {"quantizations": ["bf16", "fp16", "fp8"], "ignore": BLOCKED_PROVIDERS, "allow_fallbacks": True}


@dataclass
class ChatResult:
    text: str = ""
    provider: str | None = None
    cost: float = 0.0
    finish_reason: str | None = None
    error: str | None = None
    usage: dict = field(default_factory=dict)
    # The answer limit was lowered to fit the model's context window: as long as it can ever get.
    capped: bool = False


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


# Reasoning models can spend thousands of tokens thinking before they answer; at 8192 many answers
# came back empty ("length"). Answers truncated under a lower limit are re-run (see run.py).
MAX_TOKENS = 32768


def chat(model: dict, prompt: str, max_tokens: int = MAX_TOKENS, timeout: int = 180) -> ChatResult:
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

    last_err, capped = None, False
    for attempt in range(4):
        try:
            d = _post("/chat/completions", body, timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            last_err = f"HTTP {e.code}: {detail}"
            if e.code == 404 and model.get("provider") is None and "quantizations" in body["provider"]:
                # No endpoint matches the precision filter: accept any precision,
                # but still never a blocked provider.
                body["provider"] = {"ignore": BLOCKED_PROVIDERS, "allow_fallbacks": True}
                continue
            m = re.search(r"maximum context length is (\d+) tokens.*?\((\d+) of text input", detail)
            if e.code == 400 and m and not capped:
                # Models with a 32k window can't take a 32k answer on top of the prompt.
                body["max_tokens"] = int(m.group(1)) - int(m.group(2)) - 256
                capped = True
                continue
            if e.code in (408, 429, 500, 502, 503, 504):
                time.sleep(5 * 2 ** attempt)
                continue
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, ValueError) as e:
            # ValueError: the body wasn't valid JSON — OpenRouter sends whitespace keep-alives
            # on slow requests and the connection can drop before the real response arrives.
            # A request that timed out once (very long reasoning, stuck provider) is
            # retried once; the error is recorded and retried on the next daily run.
            last_err = f"network: {e}"
            if attempt >= 1:
                break
            time.sleep(3)
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
            capped=capped,
        )
    return ChatResult(error=last_err or "unknown error")


def decide(model: dict, state, questions: dict, timeout: int = 120) -> ChatResult:
    """Call a decision model through OpenRouter's Decisions API. `text` holds the raw answers as JSON."""
    body = {"model": model["openrouter_id"], "state": state, "questions": questions}
    if model.get("provider"):
        body["provider"] = model["provider"]
    last_err = None
    for attempt in range(3):
        try:
            d = _post_abs("https://openrouter.ai/api/alpha/decisions", body, timeout)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code in (408, 429, 500, 502, 503, 504):
                time.sleep(5 * 2 ** attempt)
                continue
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, ValueError) as e:
            last_err = f"network: {e}"
            time.sleep(3)
            continue
        usage = d.get("usage") or {}
        return ChatResult(text=json.dumps(d.get("answers") or {}), provider=d.get("provider"),
                          cost=float(usage.get("cost") or 0), finish_reason="decision",
                          usage={"prompt_tokens": usage.get("input_tokens"), "completion_tokens": usage.get("output_tokens")})
    return ChatResult(error=last_err or "unknown error")


def _post_abs(url: str, body: dict, timeout: int) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "X-Title": "Model Tested", "HTTP-Referer": "https://modeltested.com"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# ---------- local models (Ollama on the Mac test machine) ----------

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not OLLAMA.startswith("http"):
    OLLAMA = "http://" + OLLAMA
# Room for the prompt on top of the answer. Ollama's default context is a few thousand tokens,
# which would silently cut reasoning models off mid-thought.
PROMPT_ROOM = 8192


def _ollama(path: str, body: dict | None = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ollama_quant(tag: str) -> str | None:
    """Quantization of a pulled model, e.g. "Q4_K_M"."""
    return (_ollama("/api/show", {"model": tag}).get("details") or {}).get("quantization_level")


def ollama_chat(model: dict, prompt: str, timeout: int = 4 * 3600) -> ChatResult:
    max_tokens = model.get("max_tokens", MAX_TOKENS)
    options = {"num_predict": max_tokens, "num_ctx": model.get("num_ctx", max_tokens + PROMPT_ROOM)}
    if "temperature" in model:
        options["temperature"] = model["temperature"]
    body = {"model": model["ollama_tag"], "messages": [{"role": "user", "content": prompt}], "stream": False,
            "options": options}
    if "think" in model:
        body["think"] = model["think"]
    try:
        d = _ollama("/api/chat", body, timeout)
    except urllib.error.HTTPError as e:
        return ChatResult(error=f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, ValueError) as e:
        return ChatResult(error=f"ollama: {e}")
    if d.get("error"):
        return ChatResult(error=f"ollama: {str(d['error'])[:300]}")
    return ChatResult(
        text=(d.get("message") or {}).get("content") or "",
        provider=f"ollama/{model.get('quant') or 'local'}",
        finish_reason=d.get("done_reason"),
        usage={"prompt_tokens": d.get("prompt_eval_count"), "completion_tokens": d.get("eval_count")},
    )


def list_models() -> list[dict]:
    # output_modalities=all: the default list hides non-text models such as decision models.
    with urllib.request.urlopen(API + "/models?output_modalities=all", timeout=60) as r:
        return json.loads(r.read())["data"]
