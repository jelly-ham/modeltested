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

# Largest model we consider "runnable locally": a Q4 of ~130B fits a 128 GB Mac or a
# 128 GB unified-memory PC (Strix Halo, DGX Spark).
MAX_PARAMS_B = 130

# Orgs whose official open-weight releases we track automatically. Community
# fine-tunes can still be added by hand.
ORG_ALLOWLIST = {
    "qwen", "google", "meta-llama", "mistralai", "microsoft", "openai", "deepseek", "z-ai", "nvidia",
    "ibm-granite", "liquid", "moonshotai", "allenai", "baidu", "tencent", "minimax", "stepfun-ai",
    "inclusionai", "xiaomi", "cohere", "arcee-ai", "ai21", "bytedance-seed", "thudm",
    "meta", "prism-ml", "poolside", "nex-agi", "rekaai", "thinkingmachines",
}

# Hugging Face can't report a size for GGUF-only repos; fill in what the model card states.
KNOWN = {
    # Ternary weights (-1/0/1): llama.cpp's TQ2_0 format stores them at ~2.06 bits per weight.
    # Architecture is Qwen3.8-27B's (copied in models.json for the KV-cache estimate).
    "prism-ml/ternary-bonsai-2-27b": {"params_b": 27.78, "native_quant": {"name": "TQ2_0", "bpw": 2.06}},
}

SKIP_SUFFIXES = (":free", ":batch", ":beta", ":extended", ":thinking", ":nitro", ":floor", ":online")

# Specialized models (safety classifiers, translation-only, speech) aren't general assistants.
SPECIALIZED = re.compile(r"guard|safety|safeguard|-mt\d|voxtral|embed|rerank|schematron", re.I)


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
        # The block list is about corrupted generated text; decision models return probabilities, not text.
        usable = providers if m.get("kind") == "decision" else [p for p in providers if p not in client.BLOCKED_PROVIDERS]
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


def _recheck_ignored(doc: dict) -> None:
    """Forget "ignored" verdicts that the current rules no longer support, so they're checked again."""
    ignored = doc.get("ignored", {})
    for oid, why in list(ignored.items()):
        org = oid.split("/", 1)[0]
        too_big = re.match(r"([\d.]+)B params > ", why)
        if (why.startswith("org '") and org in ORG_ALLOWLIST) or (too_big and float(too_big.group(1)) <= MAX_PARAMS_B):
            del ignored[oid]


def main(args) -> None:
    doc = load_models()
    _recheck_ignored(doc)
    known = {m["openrouter_id"] for m in doc["models"] if m.get("openrouter_id")} | set(doc.get("ignored", {}))
    added = []
    for m in client.list_models():
        oid = m["id"]
        if oid in known or oid.startswith("~") or oid.endswith(SKIP_SUFFIXES):
            continue
        hf = m.get("hugging_face_id")
        org = oid.split("/", 1)[0]
        outputs = (m.get("architecture") or {}).get("output_modalities") or ["text"]
        if "decisions" in outputs:
            # Decision models (state + typed questions -> probabilities) get their own ranking;
            # open weights are not required and there is no size limit.
            doc["models"].append({
                "slug": slugify(oid.split("/", 1)[1]), "name": m.get("name", oid).split(": ", 1)[-1],
                "status": "auto", "kind": "decision", "openrouter_id": oid, "hf_id": hf, "org": org,
                "params_b": hf_params_b(hf) if hf else None, "active_params_b": None, "arch": None,
                "ollama": None, "added": today(),
            })
            added.append(oid)
            print(f"added decision model: {oid}")
            continue
        if "text" not in outputs:
            doc.setdefault("ignored", {})[oid] = f"output is {'/'.join(outputs)}, not text"
            continue
        if not hf:
            doc.setdefault("ignored", {})[oid] = "no open weights linked"
            continue
        if org not in ORG_ALLOWLIST:
            doc.setdefault("ignored", {})[oid] = f"org '{org}' not on allowlist"
            continue
        if SPECIALIZED.search(oid):
            doc.setdefault("ignored", {})[oid] = "specialized model, not a general assistant"
            continue
        known_info = KNOWN.get(oid, {})
        params = known_info.get("params_b") or hf_params_b(hf)
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
        if "native_quant" in known_info:
            entry["native_quant"] = known_info["native_quant"]
        doc["models"].append(entry)
        added.append(oid)
        print(f"added: {oid} ({params}B)")
    check_availability(doc)
    if args.dry_run:
        print(f"dry run: would add {len(added)} models")
        return
    save_models(doc)
    print(f"added {len(added)} models")
