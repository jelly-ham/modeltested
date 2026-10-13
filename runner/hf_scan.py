"""Find popular new open models on Hugging Face that OpenRouter doesn't serve.

`discover` only sees what OpenRouter lists, so models released only as weights
(e.g. Ornith 1.5) slip past it. This scans the most-downloaded recent repos,
folds quantized copies (GGUF, FP8, MLX...) into the model they quantize, and
keeps original releases only: no fine-tunes, merges or "uncensored" variants.

Models small enough for the 16 GB Mac are added as status "local" (Ollama pulls
a Q4_K_M GGUF from Hugging Face). Bigger ones go under "hf_watch" for a human to
decide. Anything rejected is recorded under "hf_ignored" so it isn't re-checked.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from . import client
from .common import load_models, save_models, slugify, today
from .discover import MAX_PARAMS_B, SPECIALIZED, hf_arch, hf_params_b

HF = "https://huggingface.co/api/models"
PIPELINES = ("text-generation", "image-text-to-text")
MAX_AGE_DAYS = 150
MIN_DOWNLOADS = 300_000   # last 30 days, summed over the model and its quantized copies
MIN_LIKES = 20            # on the original repo; download counts alone are easy to inflate
MAC_MAX_PARAMS_B = 14     # a Q4 plus 8k context fits a 16 GB Mac
QUANT_SUFFIX = re.compile(r"[-_](gguf|mlx.*|fp8|nvfp4|awq|gptq.*|int[48].*|\d+bit)$", re.I)
VARIANT = re.compile(r"uncensored|abliterat|obliterat|heretic|nsfw|roleplay|rp\b", re.I)
# Speculative-decoding drafts, OCR and diffusion models can't stand in for a chat model in Ollama.
NOT_CHAT = re.compile(r"dspark|eagle|draft|-mtp\b|ocr|diffusion", re.I)
# Repos that publish GGUFs of other people's models; tried in order for a Q4_K_M.
GGUF_PUBLISHERS = ("unsloth", "bartowski", "lmstudio-community", "ggml-org")


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None


def _base(tags: list[str], kind: str) -> str | None:
    for t in tags:
        if t.startswith(f"base_model:{kind}:"):
            return t.split(":", 2)[2]
    return None


def root_of(repo: dict) -> str:
    """The model a repo is a copy of: its quantization base, or its own name minus a format suffix."""
    tags = repo.get("tags") or []
    base = _base(tags, "quantized")
    if base:
        return base
    org, name = repo["id"].split("/", 1)
    return f"{org}/{QUANT_SUFFIX.sub('', name)}"


def popular_roots() -> dict[str, int]:
    since = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()
    seen: dict[str, dict] = {}
    for p in PIPELINES:
        for repo in _get(f"{HF}?pipeline_tag={p}&sort=downloads&limit=500") or []:
            seen[repo["id"]] = repo
    roots: dict[str, int] = {}
    for repo in seen.values():
        if repo.get("createdAt", "") < since:
            continue
        r = root_of(repo)
        roots[r] = roots.get(r, 0) + repo.get("downloads", 0)
    return roots


def find_gguf(root: str) -> str | None:
    """An Ollama tag for a Q4_K_M GGUF of `root`: the author's own GGUF repo first, then known publishers."""
    org, name = root.split("/", 1)
    candidates = [f"{org}/{name}-GGUF"] + [f"{p}/{name}-GGUF" for p in GGUF_PUBLISHERS] + [f"bartowski/{org}_{name}-GGUF"]
    for repo in candidates:
        info = _get(f"{HF}/{repo}")
        files = [s["rfilename"] for s in (info or {}).get("siblings", [])]
        if any("q4_k_m" in f.lower() and f.endswith(".gguf") for f in files):
            return f"hf.co/{repo}:Q4_K_M"
    return None


def check(root: str, downloads: int) -> tuple[str, dict | str]:
    """("add", entry) / ("watch", info) / ("ignore", reason)."""
    if downloads < MIN_DOWNLOADS:
        return "skip", ""  # not ignored: it may get popular later
    if VARIANT.search(root):
        return "ignore", "community variant (uncensored/abliterated/...)"
    if SPECIALIZED.search(root) or NOT_CHAT.search(root):
        return "ignore", "specialized model, not a general assistant"
    if root.split("/", 1)[0].lower() in GGUF_PUBLISHERS:
        return "ignore", "re-upload by a quantizer, not an original release"
    info = _get(f"{HF}/{root}")
    if not info:
        return "skip", ""
    tags = info.get("tags") or []
    for kind in ("finetune", "merge", "adapter"):
        base = _base(tags, kind)
        if base:
            return "ignore", f"{kind} of {base}"
    if (info.get("likes") or 0) < MIN_LIKES:
        return "skip", ""
    params = hf_params_b(root)
    if params is None:
        return "skip", ""
    if params > MAX_PARAMS_B:
        return "ignore", f"{params}B params > {MAX_PARAMS_B}B"
    org = root.split("/", 1)[0]
    license_ = (info.get("cardData") or {}).get("license")
    if params > MAC_MAX_PARAMS_B:
        return "watch", {"params_b": params, "downloads_30d": downloads, "license": license_, "seen": today()}
    tag = find_gguf(root)
    if not tag:
        return "watch", {"params_b": params, "downloads_30d": downloads, "license": license_,
                         "seen": today(), "why": "no Q4_K_M GGUF found yet"}
    name = root.split("/", 1)[1].replace("-", " ")
    return "add", {
        "slug": slugify(root.split("/", 1)[1]) + "-q4-mac", "name": f"{name} (Q4, Mac)", "status": "local",
        "backend": "ollama", "ollama_tag": tag, "quant": "Q4_K_M", "base": None, "openrouter_id": None,
        "hf_id": root, "org": org.lower(), "params_b": params, "active_params_b": None, "arch": hf_arch(root),
        "native_quant": {"name": "Q4_K_M", "bpw": 4.85}, "ollama": tag, "license": license_, "added": today(),
        "note": "Found by the Hugging Face scan; not on OpenRouter. Name is from the repo; check it before publishing.",
    }


def _stem(repo_id: str) -> tuple[str, float | None]:
    """("ornith-ai/ornith-#-9b", 1.5) for "ornith-ai/Ornith-1.5-9B": the name with its version taken out."""
    m = re.search(r"(\d+(?:\.\d+)?)", repo_id.split("/", 1)[1])
    if not m:
        return repo_id.lower(), None
    org, name = repo_id.split("/", 1)
    return f"{org}/{name[:m.start()]}#{name[m.end():]}".lower(), float(m.group(1))


def main(args) -> None:
    doc = load_models()
    known = {(m.get("hf_id") or "").lower() for m in doc["models"]}
    known |= {(m.get("hugging_face_id") or "").lower() for m in client.list_models()}  # discover's job
    known |= {k.lower() for k in doc.get("hf_ignored", {})}
    known |= {k.lower() for k, v in doc.get("hf_watch", {}).items() if "why" not in v}  # no-GGUF ones are re-checked
    known.discard("")
    # Mirrors under another org share the model's name; only the most-downloaded copy counts.
    names = {k.split("/", 1)[-1].lower() for k in known}
    roots = popular_roots()
    newest: dict[str, float] = {}  # stem -> highest version seen, so an older release isn't added next to a newer one
    for r in list(known) + list(roots):
        stem, ver = _stem(r)
        if ver is not None:
            newest[stem] = max(newest.get(stem, ver), ver)
    added = 0
    for root, downloads in sorted(roots.items(), key=lambda kv: -kv[1]):
        name = root.split("/", 1)[1].lower()
        if root.lower() in known or name in names:
            continue
        names.add(name)
        stem, ver = _stem(root)
        if ver is not None and newest[stem] > ver:
            doc.setdefault("hf_ignored", {})[root] = "older version; a newer one exists"
            continue
        verdict, data = check(root, downloads)
        if verdict == "add":
            doc["models"].append(data)
            added += 1
            print(f"added (Mac Q4): {root} ({data['params_b']}B, {downloads:,} downloads/30d)")
        elif verdict == "watch":
            doc.setdefault("hf_watch", {})[root] = data
            print(f"watch ({data.get('why', 'too big for the 16 GB Mac')}): {root} ({data['params_b']}B, {downloads:,} downloads/30d)")
        elif verdict == "ignore":
            doc.setdefault("hf_ignored", {})[root] = data
    if args.dry_run:
        print(f"dry run: would add {added} models")
        return
    save_models(doc)
    print(f"added {added} models")
