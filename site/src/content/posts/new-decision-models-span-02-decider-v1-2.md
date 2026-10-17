---
title: "7 new decision models tested: Span-02 takes #1, Drex v2.0 goes backwards"
dek: "Span-02, Jev 1.14, Decider V1.2 and Flash V1.2, d1-ultra, Drex v2.0 and Classify-1 all landed on OpenRouter this week. Each one against the version before it."
date: 2026-10-17
category: News
tags: [News, Decision models, Rankings]
cover:
  label: "Decision accuracy · new this week"
  compare:
    - { label: "Span-02", value: 96.4 }
    - { label: "Jev 1.14", value: 92.9 }
    - { label: "Drex v2.0", value: 87.5 }
---

Seven new decision models showed up on OpenRouter between October 13 and 17. We ran each one through the same 56 situations as the other [decision models](/best-decision-models/): routing support tickets, applying refund rules, spotting phishing, flagging risky code changes. 19 of the 56 are hard ones, with a catch buried in the details.

## The short version

| Model | Accuracy | Hard ones | Rank (of 22) | Version before it |
|---|---|---|---|---|
| [Span-02](/decision-models/span-02/) | 96.4 | 94.7 | #1 | Span-01: couldn't test |
| [Jev 1.14](/decision-models/jev-1-14/) | 92.9 | 84.2 | #4 | Jev 1.13: 92.0, hard 78.9 |
| [Decider V1.2](/decision-models/pplx-decider-v1-2/) | 91.1 | 81.6 | #7 | V1.1: 91.1, hard 84.2 |
| [Decider Flash V1.2](/decision-models/pplx-decider-flash-v1-2/) | 91.1 | 84.2 | #9 | (new) |
| [d1-ultra](/decision-models/d1-ultra/) | 90.2 | 81.6 | #10 | d1: 86.6, hard 73.7 |
| [Drex v2.0](/decision-models/drex-v2-0/) | 87.5 | 76.3 | #13 | Drex v1.5: 92.0, hard 84.2 |
| [Classify-1](/decision-models/classify-1/) | 86.9 | 71.1 | #15 | (new) |

Accuracy is out of 100. Ties share a score but are listed in the order on our [rankings page](/best-decision-models/).

## Span-02: new #1

Respan's Span-02 got 54 of 56 right and 18 of the 19 hard ones. That puts it just ahead of [Solar Decide](/decision-models/solar-decide/) (95.5), the previous #1. It also costs less: about $0.004 per 1,000 calls, against $0.05 for Solar Decide.

We couldn't test Respan's earlier Span-01 and Span-01 Lite. Their API only took yes/no questions about a chat transcript, and most of our situations are multiple choice. Span-02 takes the same format as the other decision models.

## Jev 1.14 and d1-ultra: real improvements

Typesafe's Jev 1.14 moves up from 92.0 to 92.9 overall, but the bigger change is on the hard situations: 16 of 19, up from 15. Same price as 1.13, about $0.02 per 1,000 calls.

Liquid's d1-ultra is the biggest jump of the week over its sibling: 90.2 against 86.6 for [d1](/decision-models/d1/), and 81.6 against 73.7 on the hard ones. It costs about $0.01 per 1,000 calls, the same as d1.

## Decider V1.2: no change

Perplexity's Decider V1.2 scores exactly what V1.1 did, 91.1, and is slightly worse on the hard situations (81.6 against 84.2). The new Flash V1.2 also scores 91.1 and keeps V1.1's 84.2 on the hard ones, at about half V1.2's price ($0.002 against $0.005 per 1,000 calls). If you use Decider, Flash V1.2 is the one to try.

## Drex v2.0: worse than v1.5

Nace AI's Drex v2.0 scored 87.5, down from 92.0 for [Drex v1.5](/decision-models/drex-v1-5/), and 76.3 against 84.2 on the hard ones. Same price. Drex v1.5 also has downloadable weights; we found none for v2.0 yet. For now we'd stay on v1.5.

## Classify-1

ScaleDown's Classify-1 lands at 86.9, #15 of 22, and is the priciest of the new ones at about $0.03 per 1,000 calls. A note on how we ran it: its API only accepts plain text, so for the situations that come as structured data (a ticket with fields, a list of transactions), we send it the same JSON text the regular LLMs get. The other decision models take the structured data directly.

## Still behind regular LLMs

None of the new models closes the gap to regular open models. Eight of them score 99 or more on the same 56 situations, and [gpt-oss-120b](/models/gpt-oss-120b/) does it for about $0.09 per 1,000 calls. The new decision models cost $0.002 to $0.03 per 1,000 calls, so 3 to 40 times less; whether that's worth a few extra mistakes depends on what the decision is. We went through the numbers in [what each call really costs](/posts/decision-models-cost/).

Full results, including how honest each model's confidence is, are on the [decision model rankings](/best-decision-models/). For how we grade, see [how we test](/best-local-llms/methodology/).
