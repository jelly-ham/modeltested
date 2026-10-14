"""Measure hidden prompt overhead on decision models.

Sends synthetic requests (no benchmark content) of growing length and prints the billed input
tokens, so we can see whether the vendor's own instructions add a flat per-call amount.

    OPENROUTER_API_KEY=... python3 scripts/probe_overhead.py upstage/solar-decide upstage/solar-decide-flash
"""
import json
import statistics as st
import sys
import urllib.request
import os

SENTENCE = "The customer wrote in about an order that arrived late and asked what we can do. "
YESNO = {"type": "noul", "instructions": "Is the customer asking for a refund?"}
EXTRA = {
    "team": {"type": "choice", "instructions": "Which team should handle this?",
             "criteria": {"billing": "Payments and refunds", "shipping": "Deliveries and tracking", "technical": "Bugs and outages"}},
    "urgency": {"type": "score", "instructions": "How urgent is it?",
                "criteria": ["Can wait a week", "Within a few days", "Today", "Immediately"]},
}


def call(model: str, state: str, questions: dict) -> tuple[int, int, float]:
    req = urllib.request.Request("https://openrouter.ai/api/alpha/decisions",
                                 data=json.dumps({"model": model, "state": state, "questions": questions}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                          "Content-Type": "application/json", "X-Title": "Model Tested"})
    with urllib.request.urlopen(req, timeout=120) as r:
        u = json.loads(r.read()).get("usage") or {}
    return u.get("input_tokens"), u.get("output_tokens"), float(u.get("cost") or 0)


def main() -> None:
    for model in sys.argv[1:]:
        print(f"\n== {model}")
        print(f"{'case':<28}{'state chars':>12}{'billed in':>11}{'out':>5}")
        rows = []
        for reps in (0, 0, 1, 4, 16, 64, 256):
            state = "Hi." if reps == 0 else SENTENCE * reps
            tin, tout, _ = call(model, state, {"refund": YESNO})
            rows.append((reps, tin))
            print(f"{'1 question, ' + str(reps) + ' sentences':<28}{len(state):>12}{tin:>11}{tout:>5}")
        for qs, label in (({"refund": YESNO, **EXTRA}, "3 questions, 4 sentences"),):
            tin, tout, _ = call(model, SENTENCE * 4, qs)
            print(f"{label:<28}{len(SENTENCE * 4):>12}{tin:>11}{tout:>5}")
        x = [r for r, _ in rows]
        y = [t for _, t in rows]
        slope, icept = st.linear_regression(x, y)
        print(f"fit: billed = {icept:.0f} + {slope:.1f} per sentence (one sentence is ~17 tokens of text)")


if __name__ == "__main__":
    main()
