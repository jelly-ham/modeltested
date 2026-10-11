"""Find new open-weight models on OpenRouter and add them to bench/models.json.

A model qualifies when OpenRouter links it to a Hugging Face repo (i.e. the
weights are public), its org is on the allowlist, and it is small enough to run
locally. Everything else is recorded under "ignored" so it isn't re-checked.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import client
from .common import load_models, save_models, slugify, today

MAX_PARAMS_B = 40  # largest model we consider "runnable locally" for now

# Orgs whose official open-weight releases we track automatically. Community
# fine-tunes can still be added by hand.
ORG_ALLOWLIST = {
    "qwen", "google", "meta-llama", "mistralai", "microsoft", "openai", "deepseek", "z-ai", "nvidia",
    "ibm-granite", "liquid", "moonshotai", "allenai", "baidu", "tencent", "minimax", "stepfun-ai",
    "inclusionai", "xiaomi", "cohere", "arcee-ai", "ai21", "bytedance-seed", "thudm",
}

SKIP_SUFFIXES = (":free", ":batch", ":beta", ":extended", ":thinking", ":nitro", ":floor", ":online")

# Specialized models (safety classifiers, translation-only, speech) aren't general assistants.
SPECIALIZED = re.compile(r"guard|safety|safeguard|-mt\d|voxtral|embed|rerank", re.I)


def _hf_json(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None


def hf_params_b(hf_id: str) -> float | None:
    info = _hf_json(f"https://huggingface.co/api/models/{hf_id}") or {}
    total = (info.get("safetensors") or {}).get("total")
    return round(total / 1e9, 2) if total else None


def hf_arch(hf_id: str) -> dict | None:
    """Layer/head counts for the KV-cache estimate. Gated repos return None."""
    cfg = _hf_json(f"https://huggingface.co/{hf_id}/resolve/main/config.json")
    if not cfg:
        return None
    cfg = cfg.get("text_config", cfg)  # multimodal configs nest the LM
    layers = cfg.get("num_hidden_layers")
    heads = cfg.get("num_attention_heads")
    kv = cfg.get("num_key_value_heads") or heads
    head_dim = cfg.get("head_dim") or (cfg["hidden_size"] // heads if cfg.get("hidden_size") and heads else None)
    if not (layers and kv and head_dim):
        return None
    return {"layers": layers, "kv_heads": kv, "head_dim": head_dim}


def active_params_b(*names: str) -> float | None:
    for n in names:
        m = re.search(r"-a(\d+(?:\.\d+)?)b\b", n.lower())
        if m:
            return float(m.group(1))
    return None


def endpoint_providers(openrouter_id: str) -> list[str] | None:
    """Provider names currently serving a model; [] if OpenRouter no longer lists it, None on other errors."""
    try:
        with urllib.request.urlopen(f"{client.API}/models/{openrouter_id}/endpoints", timeout=30) as r:
            return [e.get("provider_name") for e in json.loads(r.read())["data"]["endpoints"]]
    except urllib.error.HTTPError as e:
        return [] if e.code == 404 else None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None


def check_availability(doc: dict) -> None:
    """Park models that only blocked providers serve, and bring them back when that changes.

    Without this they fail every request on every run ("All providers have been ignored").
    """
    for m in doc["models"]:
        status = m.get("status")
        if status not in ("active", "auto", "unavailable") or m["openrouter_id"].startswith("mock:"):
            continue
        providers = endpoint_providers(m["openrouter_id"])
        if providers is None:
            continue  # couldn't check; leave as is
        usable = [p for p in providers if p not in client.BLOCKED_PROVIDERS]
        if not usable and status != "unavailable":
            m["previous_status"] = status
            m["status"] = "unavailable"
            m["unavailable_reason"] = (f"only blocked providers ({', '.join(providers)})" if providers
                                       else "no longer listed on OpenRouter")
            m["unavailable_since"] = today()
            print(f"unavailable: {m['openrouter_id']} ({m['unavailable_reason']})")
        elif usable and status == "unavailable":
            m["status"] = m.pop("previous_status", "active")
            m.pop("unavailable_reason", None)
            m.pop("unavailable_since", None)
            print(f"available again: {m['openrouter_id']} via {', '.join(usable)}")


def main(args) -> None:
    doc = load_models()
    known = {m["openrouter_id"] for m in doc["models"]} | set(doc.get("ignored", {}))
    added = []
    for m in client.list_models():
        oid = m["id"]
        if oid in known or oid.startswith("~") or oid.endswith(SKIP_SUFFIXES):
            continue
        hf = m.get("hugging_face_id")
        org = oid.split("/", 1)[0]
        if not hf:
            doc.setdefault("ignored", {})[oid] = "no open weights linked"
            continue
        if org not in ORG_ALLOWLIST:
            doc.setdefault("ignored", {})[oid] = f"org '{org}' not on allowlist"
            continue
        if SPECIALIZED.search(oid):
            doc.setdefault("ignored", {})[oid] = "specialized model, not a general assistant"
            continue
        params = hf_params_b(hf)
        if params is None:
            # Not ignored permanently — HF metadata may appear later.
            print(f"skip (param count unknown yet): {oid}")
            continue
        if params > MAX_PARAMS_B:
            doc.setdefault("ignored", {})[oid] = f"{params}B params > {MAX_PARAMS_B}B"
            continue
        entry = {
            "slug": slugify(oid.split("/", 1)[1]),
            "name": m.get("name", oid).split(": ", 1)[-1],
            "status": "auto",
            "openrouter_id": oid,
            "hf_id": hf,
            "org": org,
            "params_b": params,
            "active_params_b": active_params_b(oid, hf),
            "arch": hf_arch(hf),
            "ollama": None,
            "added": today(),
        }
        doc["models"].append(entry)
        added.append(oid)
        print(f"added: {oid} ({params}B)")
    check_availability(doc)
    if args.dry_run:
        print(f"dry run: would add {len(added)} models")
        return
    save_models(doc)
    print(f"added {len(added)} models")
