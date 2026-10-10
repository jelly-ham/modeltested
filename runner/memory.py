"""Estimate which quantizations fit which hardware tiers.

This is arithmetic, not measurement: weights (params x bits-per-weight) + an
fp16 KV cache at a fixed context + a fixed runtime overhead, compared with the
memory a GPU or Mac can actually hand to the model.
"""
from __future__ import annotations

# Approximate average bits per weight of common llama.cpp GGUF quants. Q8_0 is
# effectively lossless, so we never recommend going higher.
QUANTS = [("Q4_K_M", 4.85), ("Q5_K_M", 5.69), ("Q6_K", 6.59), ("Q8_0", 8.5)]
CONTEXT = 8192
OVERHEAD_GB = 0.6

TIERS = [
    {"id": "gpu-8", "label": "8 GB GPU", "kind": "gpu", "gb": 8},
    {"id": "gpu-12", "label": "12 GB GPU", "kind": "gpu", "gb": 12},
    {"id": "gpu-16", "label": "16 GB GPU", "kind": "gpu", "gb": 16},
    {"id": "gpu-24", "label": "24 GB GPU", "kind": "gpu", "gb": 24},
    {"id": "gpu-32", "label": "32 GB GPU", "kind": "gpu", "gb": 32},
    {"id": "mac-16", "label": "Mac 16 GB", "kind": "mac", "gb": 16},
    {"id": "mac-24", "label": "Mac 24 GB", "kind": "mac", "gb": 24},
    {"id": "mac-32", "label": "Mac 32 GB", "kind": "mac", "gb": 32},
    {"id": "mac-48", "label": "Mac 48 GB", "kind": "mac", "gb": 48},
    {"id": "mac-64", "label": "Mac 64 GB", "kind": "mac", "gb": 64},
]


def usable_gb(tier: dict) -> float:
    if tier["kind"] == "gpu":
        return tier["gb"] - 0.5  # driver/display reservation
    # macOS lets the GPU wire roughly 2/3 of RAM up to 36 GB, 3/4 above (default limit).
    return tier["gb"] * (2 / 3 if tier["gb"] <= 36 else 0.75)


def kv_cache_gb(model: dict, context: int = CONTEXT) -> float:
    a = model.get("arch") or {}
    if all(a.get(k) for k in ("layers", "kv_heads", "head_dim")):
        return 2 * a["layers"] * a["kv_heads"] * a["head_dim"] * context * 2 / 1e9
    # Unknown architecture: conservative guess that grows with model size.
    p = model.get("params_b") or 8
    return 0.5 if p < 10 else 1.0 if p < 20 else 1.5


def quant_options(model: dict) -> list[tuple[str, float]]:
    nq = model.get("native_quant")
    if nq:  # e.g. gpt-oss ships as MXFP4 — that's what everyone runs
        return [(nq["name"], nq["bpw"])]
    return QUANTS


def estimate(model: dict) -> dict | None:
    p = model.get("params_b")
    if not p:
        return None
    kv = kv_cache_gb(model)
    need = {name: round(p * bpw / 8 + kv + OVERHEAD_GB, 1) for name, bpw in quant_options(model)}
    tiers = {}
    for t in TIERS:
        fitting = [name for name, gb in need.items() if gb <= usable_gb(t)]
        tiers[t["id"]] = fitting[-1] if fitting else None  # highest-precision quant that fits
    return {"context": CONTEXT, "kv_cache_gb": round(kv, 2), "need_gb": need, "best_quant_by_tier": tiers}
