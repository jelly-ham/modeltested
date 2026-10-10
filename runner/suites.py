"""Prompt construction and scoring for each suite."""
from __future__ import annotations

import json
import re

CODING_SUFFIX = """

Write the solution in Python 3.12 using only the standard library. Reply with a single ```python code block containing the complete implementation (including imports). Do not include tests or example usage."""

EXTRACT_TEMPLATE = """Extract information from the text below.

Reply with ONLY a JSON object (no prose, no markdown) with exactly these keys:
{fields}

Rules:
- Use null when a value is not stated and cannot be derived from the text.
- Dates as YYYY-MM-DD unless another format is specified. Numbers as JSON numbers (no currency symbols, units or thousands separators).
{rules}
Text:
\"\"\"
{text}
\"\"\""""


def build_prompt(suite: str, q: dict) -> str:
    if suite == "coding":
        return q["prompt"] + CODING_SUFFIX
    if suite == "extract":
        rules = f"- {q['rules']}\n" if q.get("rules") else ""
        return EXTRACT_TEMPLATE.format(fields=q["fields"], rules=rules, text=q["text"])
    raise ValueError(suite)


def strip_think(text: str) -> str:
    # Some providers inline chain-of-thought in the content.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    return text.strip()


# ---------- coding ----------

def extract_code(text: str) -> str:
    text = strip_think(text)
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S | re.I)
    if blocks:
        return max(blocks, key=len)
    return text


def coding_case(q: dict, answer: str) -> str:
    return extract_code(answer) + "\n\n# ---- tests ----\n" + q["tests"]


# ---------- extraction ----------

def parse_json_output(text: str) -> tuple[object | None, bool]:
    """Returns (parsed, strict) — strict means the reply was bare JSON as instructed."""
    text = strip_think(text)
    try:
        return json.loads(text), True
    except ValueError:
        pass
    m = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.S | re.I)
    candidates = [m.group(1)] if m else []
    i, j = text.find("{"), text.rfind("}")
    if 0 <= i < j:
        candidates.append(text[i:j + 1])
    for c in candidates:
        try:
            return json.loads(c), False
        except ValueError:
            continue
    return None, False


def _flatten(x, path="$"):
    if isinstance(x, dict):
        if not x:
            yield path, {}
        for k, v in x.items():
            yield from _flatten(v, f"{path}.{k}")
    elif isinstance(x, list):
        if not x:
            yield path, []
        for i, v in enumerate(x):
            yield from _flatten(v, f"{path}[{i}]")
    else:
        yield path, x


def _norm_str(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().casefold()).rstrip(".")


def _as_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").replace("$", "").strip())
        except ValueError:
            return None
    return None


def values_equal(expected, got) -> bool:
    if expected is None or got is None:
        return expected is None and got is None
    if isinstance(expected, bool) or isinstance(got, bool):
        return isinstance(expected, bool) and isinstance(got, bool) and expected == got
    if isinstance(expected, (int, float)):
        g = _as_number(got)
        return g is not None and abs(g - expected) <= 0.005 + 1e-9 * abs(expected)
    if isinstance(expected, str):
        if isinstance(got, (int, float)):
            got = str(int(got)) if float(got).is_integer() else str(got)
        return isinstance(got, str) and _norm_str(expected) == _norm_str(got)
    return expected == got  # empty {} / [] markers


def score_extract(expected: dict, got) -> tuple[float, dict]:
    if not isinstance(got, dict):
        return 0.0, {"error": "no JSON object"}
    exp = dict(_flatten(expected))
    out = dict(_flatten(got))
    paths = set(exp) | set(out)
    matched = [p for p in exp if p in out and values_equal(exp[p], out[p])]
    wrong = sorted(p for p in paths if p not in matched)
    return len(matched) / len(paths), {"matched": len(matched), "total": len(paths), "wrong": wrong}
