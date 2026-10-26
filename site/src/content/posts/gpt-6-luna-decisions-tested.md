---
title: "GPT-6 Luna Decisions tested: OpenAI's decision model ranks #13 of 23"
dek: "OpenAI's entry in the decision model race got 89.3% of our 56 real decisions right. Twelve decision models did better, most of them for less money, and so did plenty of free open models."
date: 2026-10-26
category: News
tags: [News, Decision models, Rankings]
cover:
  label: "Decision accuracy"
  compare:
    - { label: "Span-02", value: 96.4 }
    - { label: "gpt-oss-20b", value: 94.6 }
    - { label: "GPT-6 Luna Decisions", value: 89.3 }
---

GPT-6 Luna Decisions is OpenAI's model for the new Decisions API. It's [GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna), the small, cheap member of the GPT-6 family. It doesn't write an answer; it reads a situation and returns a probability for each option. It's the only OpenAI decision model on OpenRouter right now, and we ran it through the same 56 situations as every other [decision model](/best-decision-models/): routing support tickets, applying refund and expense rules, spotting phishing, triaging incidents. 19 of the 56 are hard ones, with the catch buried in the details.

## The short version

| | GPT-6 Luna Decisions |
|---|---|
| Accuracy (56 situations) | 89.3 |
| Hard ones (19) | 78.9 |
| Calibration | 94.5, #6 of 23 |
| Rank among decision models | #13 of 23 |
| Cost | about $0.04 per 1,000 calls |

It's a middling result. Not bad, but you don't get much for the OpenAI name.

## Compared with the other decision models

| Model | Accuracy | Hard ones | Cost per 1,000 calls |
|---|---|---|---|
| [Span-02](/decision-models/span-02/) | 96.4 | 94.7 | under $0.01 |
| [Solar Decide](/decision-models/solar-decide/) | 95.5 | 94.7 | $0.05 |
| [Drex Max](/decision-models/drex-max/) | 93.8 | 92.1 | $0.02 |
| [Mercury Decide](/decision-models/mercury-decide/) | 93.8 | 89.5 | under $0.01 |
| [GPT-6 Luna Decisions](/decision-models/gpt-6-luna-decisions/) | 89.3 | 78.9 | $0.04 |

The gap is mostly on the hard situations: Luna got 13 of the 19 fully right, the top two got 17. The current #1, Span-02, is more accurate across the board and costs about a tenth as much.

The price is all input. OpenRouter charges $0.10 per million input tokens and nothing for output, and a call to Luna averaged about 420 billed input tokens on our public questions. That's less than Solar Decide (about 1,040, most of it the vendor's own instructions) but more than Mercury Decide (about 180), which is part of why Mercury costs a tenth as much.

## Where it went wrong

Luna missed something on 10 of the 56 situations. On 8 of them it got one of two questions wrong; on 2 it got both wrong. Six of the 10 were hard ones, and most need a small calculation or a rule applied to the facts: an expense limit, fraud rules, a loan's debt-to-income ratio, a deadline across time zones. The rest were incident triage and telling a real email from phishing.

Two of the misses are in our public set, so we can show them.

**A meeting across three time zones.** Find a 45-minute slot that fits Lisbon (09:00 to 17:00, UTC+1), Bangalore (10:00 to 19:00, UTC+5:30) and New York (08:00 to 17:00, UTC−4). In UTC, New York starts at 12:00 and Bangalore ends at 13:30, so only the 12:30 start works. Luna picked 13:00 (47% sure), which runs 15 minutes past the end of Bangalore's day. It also said Bangalore's working day doesn't end first, when it does.

**A real GitHub security email.** The context says the user added a new SSH key from their own laptop two minutes earlier, and the email passes DKIM and SPF. Luna correctly said it wasn't phishing (3%), but then gave 75% that the user needs to do something about it. They don't: the email describes exactly what they just did.

Both are the kind of thing a model gets right if it works the problem step by step, which a decision model, answering in a single pass with no reasoning, doesn't do.

## Free open models do better

42 of the 90 models on our decision test beat Luna, and most of them are regular open models you can download. Some cost less to run through an API, too:

| Model | Accuracy | Hard ones | Cost per 1,000 calls |
|---|---|---|---|
| [Ling 3.0 Flash VL](/models/ling-3-0-flash-vl/) | 96.4 | 92.1 | $0.02 |
| [Nex-N2.5-Mini](/models/nex-n2-5-mini/) | 94.6 | 94.7 | $0.02 |
| [gpt-oss-20b](/models/gpt-oss-20b/) | 94.6 | 97.4 | $0.05 |
| [gpt-oss-120b](/models/gpt-oss-120b/) | 99.1 | 100 | $0.09 |

OpenAI's own open model, gpt-oss-20b, scores 5 points higher than its decision model, gets 18 of the 19 hard ones, and runs on a [16 GB graphics card](/hardware/16gb-gpu/). The catch is that regular models think before answering, so they are slower and their cost per call varies more. We went through that trade-off in [what each call really costs](/posts/decision-models-cost/).

## Should you use it?

If you're already on OpenAI and want probabilities from one API call, it works, and its confidence is fairly honest: its calibration score of 94.5 is the sixth best of the 23. But on accuracy it sits in the middle of the pack. Span-02 or Solar Decide are better decision models, and if a few seconds of thinking is acceptable, gpt-oss-20b is better still.

Full results are on the [decision model rankings](/best-decision-models/) and [GPT-6 Luna Decisions' page](/decision-models/gpt-6-luna-decisions/). For how we grade, see [how we test](/best-local-llms/methodology/).
