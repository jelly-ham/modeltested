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


DECISIONS_TEMPLATE = """Read the STATE and answer every QUESTION by assigning a probability to each allowed option.

Reply with ONLY a JSON object (no prose, no markdown): for each question id, an object mapping every allowed option to a probability between 0 and 1, summing to 1. Use your honest confidence.

STATE:
{state}

QUESTIONS:
{questions}"""


def decision_options(spec: dict) -> list[str]:
    if spec["type"] == "noul":
        return ["true", "false"]
    if spec["type"] == "choice":
        return list(spec["criteria"])
    return [str(i) for i in range(len(spec["criteria"]))]


def _describe(qid: str, spec: dict) -> str:
    opts = decision_options(spec)
    if spec["type"] == "choice":
        detail = "; ".join(f'"{k}": {v}' for k, v in spec["criteria"].items())
    elif spec["type"] == "score":
        detail = "; ".join(f'"{i}": {v}' for i, v in enumerate(spec["criteria"]))
    else:
        detail = '"true" or "false"'
    return f'- {qid}: {spec.get("instructions", "")} Options: {detail}. (allowed keys: {", ".join(opts)})'


def build_prompt(suite: str, q: dict) -> str:
    if suite == "decisions":
        state = q["state"] if isinstance(q["state"], str) else json.dumps(q["state"], indent=2)
        return DECISIONS_TEMPLATE.format(state=state, questions="\n".join(_describe(k, v) for k, v in q["questions"].items()))
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


# ---------- decisions ----------

def _normalize(spec: dict, raw: dict) -> dict[str, float]:
    opts = decision_options(spec)
    vals = {o: max(0.0, float(raw.get(o, 0) or 0)) for o in opts}
    total = sum(vals.values())
    return {o: v / total for o, v in vals.items()} if total > 0 else {}


def decisions_from_llm(text: str, questions: dict) -> dict[str, dict[str, float]]:
    parsed, _ = parse_json_output(text)
    out = {}
    if isinstance(parsed, dict):
        for qid, spec in questions.items():
            raw = parsed.get(qid)
            if isinstance(raw, dict):
                raw = {str(k).lower() if spec["type"] == "noul" else str(k): v for k, v in raw.items()
                       if isinstance(v, (int, float)) and not isinstance(v, bool)}
                out[qid] = _normalize(spec, raw)
    return out


def decisions_from_api(answers: dict, questions: dict) -> dict[str, dict[str, float]]:
    """OpenRouter /api/alpha/decisions answers -> option probabilities."""
    out = {}
    for qid, spec in questions.items():
        a = answers.get(qid) or {}
        if spec["type"] == "noul" and isinstance(a.get("noul"), (int, float)):
            out[qid] = {"true": float(a["noul"]), "false": 1 - float(a["noul"])}
            continue
        probs = a.get("probabilities") or {}
        raw = {}
        for k, v in probs.items():
            key = str(k)
            if spec["type"] == "score" and key not in decision_options(spec):
                crit = [c if isinstance(c, str) else json.dumps(c) for c in spec["criteria"]]
                key = str(crit.index(k)) if k in crit else key
            raw[key] = v
        if not raw and "choice" in a:  # only the pick, no distribution
            raw = {str(a["choice"]): 1.0}
        out[qid] = _normalize(spec, raw)
    return out


def _expected_key(spec: dict, e) -> str:
    return ("true" if e else "false") if spec["type"] == "noul" else str(e)


def score_decisions(questions: dict, expected: dict, probs: dict) -> tuple[float, dict]:
    """Accuracy over sub-questions (argmax must equal the answer key) plus a Brier score for calibration."""
    correct, briers, picks = 0, [], {}
    for qid, spec in questions.items():
        gold = _expected_key(spec, expected[qid])
        p = probs.get(qid) or {}
        pick = max(p, key=p.get) if p else None
        picks[qid] = pick
        correct += pick == gold
        briers.append(sum((p.get(o, 0.0) - (1.0 if o == gold else 0.0)) ** 2 for o in decision_options(spec)) if p else 2.0)
    n = len(questions)
    return correct / n, {"brier": round(sum(briers) / n, 4), "picks": picks}
