---
title: "Decision models vs. regular LLMs: what each call really costs"
dek: "Decision models answer in 0 to 2 tokens. The LLMs that beat them think for hundreds or thousands. We counted the tokens and the bill for 76 models."
date: 2026-10-12
category: News
tags: [News, Decision models, Rankings]
cover:
  label: "Output tokens per call · median"
  big: "2 vs 817"
---

When we published our [decision model rankings](/best-decision-models/), the most common reply was fair: decision models never claimed to be smarter than a big LLM. Their pitch is efficiency. So how much more do you pay for the extra accuracy?

We measured it. For every model we recorded the input tokens, output tokens and what OpenRouter actually billed on the 14 public questions of our decision test, then put that next to each model's accuracy on the full test (56 situations).

## The short version

- **Decision models barely write anything.** The median is 2 output tokens per call; most report 0 to 2. You pay almost only for reading the question.
- **The LLMs that beat them think first.** Regular models that score above the best decision model all reason before answering: typically 300 to 3,000 output tokens per call.
- **Input costs about the same for everyone.** Around 300 tokens per call for LLMs and 170 to 470 for most decision models. The difference is almost all output.
- **The cheapest decision models are hard to beat on price,** at under a cent per 1,000 calls. But some LLMs are close: Ling 3.0 Flash VL was more accurate than every decision model and cost less than the best one.
- **Thinking can go badly wrong.** One model averaged over 10,000 output tokens per call, cost $13 per 1,000 calls, and got only 41% right.

## Decision models

Accuracy is on all 56 situations; tokens and cost are averages per call on the 14 public ones. "Per 1,000 calls" means 1,000 situations, each with one to three questions.

| Model | Accuracy | Input tokens | Output tokens | Cost per 1,000 calls |
|---|---|---|---|---|
| [Solar Decide](/decision-models/solar-decide/) | 95.5% | 1,039 | 2 | $0.05 |
| [Mercury Decide](/decision-models/mercury-decide/) | 93.8% | 180 | 2 | $0.004 |
| [Drex v1.5](/decision-models/drex-v1-5/) | 92.0% | 172 | 113 | $0.007 |
| [Jev 1.13](/decision-models/jev-1-13/) | 92.0% | 470 | 64 | $0.02 |
| [Decider V1.1 27B](/decision-models/pplx-decider-v1-1-27b/) | 91.1% | 427 | 2 | $0.009 |
| [Microsoft-Decision-1](/decision-models/microsoft-decision-1/) | 90.2% | 186 | 2 | $0.008 |
| [GPT-6 Luna Decisions](/decision-models/gpt-6-luna-decisions/) | 89.3% | 420 | 0 | $0.04 |
| [Clef](/decision-models/clef/) | 87.5% | 387 | 0 | $0.09 |
| [d1](/decision-models/d1/) | 86.6% | 294 | 0 | $0.01 |
| [Clef Flash](/decision-models/clef-flash/) | 84.8% | 387 | 0 | $0.02 |

Solar Decide reports about 1,000 input tokens for the same questions others count as 200 to 400, probably because its provider counts its own instructions. It's still only five cents per 1,000 calls.

## Regular LLMs

| Model | Accuracy | Input tokens | Output tokens | Cost per 1,000 calls |
|---|---|---|---|---|
| [gpt-oss-120b](/models/gpt-oss-120b/) | 99.1% | 323 | 443 | $0.09 |
| [Ling 3.0 Flash](/models/ling-3-0-flash/) | 99.1% | 300 | 336 | $0.08 |
| [Muse Glimmer 30B](/models/muse-glimmer-30b/) | 99.1% | 315 | 1,026 | $1.33 |
| [Qwen3.6 27B](/models/qwen3-6-27b/) | 99.1% | 287 | 1,906 | $4.69 |
| [Laguna XS 2.1](/models/laguna-xs-2-1/) | 97.3% | 318 | 605 | $0.09 |
| [Ling 3.0 Flash VL](/models/ling-3-0-flash-vl/) | 96.4% | 300 | 280 | $0.02 |
| [gpt-oss-20b](/models/gpt-oss-20b/) | 94.6% | 323 | 343 | $0.05 |
| [Nex-N2.5-Mini](/models/nex-n2-5-mini/) | 94.6% | 318 | 180 | $0.03 |
| [Gemma 4 26B](/models/gemma-4-26b-a4b-it/) (no reasoning) | 92.0% | 290 | 73 | $0.05 |
| [Mistral Nemo](/models/mistral-nemo/) (no reasoning) | 78.0% | 281 | 73 | $0.008 |
| [Qwen3 Next 80B Thinking](/models/qwen3-next-80b-a3b-thinking/) | 41.1% | 279 | 10,834 | $13.04 |

Across all 62 regular models we priced: the 29 that reason before answering had a median of 817 output tokens, 96% accuracy and $0.55 per 1,000 calls. The 33 that answer straight away had a median of 80 output tokens, 83% accuracy and $0.06 per 1,000 calls.

## Where the money goes

Output tokens. Every model reads roughly the same question, so input costs land in a narrow band. What separates a $0.01 model from a $5 one is how much it writes before the answer.

That is also why the top of our accuracy table is all reasoning models. Our hard cases need a few steps: count the days in a refund window, convert three time zones, check an insurance claim against a yearly limit. Decision models answer in one shot and miss more of these: their accuracy on the hard cases ranged from 68% to 95%, while the best reasoning models got all of them.

Price per token matters too. Qwen3.6 27B and gpt-oss-120b are equally accurate here, but Qwen thinks four times longer and its tokens cost more, so it's about 50 times more expensive per call.

## Which should you use?

- **Millions of routine calls** (ticket routing, tagging, simple yes/no checks): a decision model. Mercury Decide and Microsoft-Decision-1 cost under a cent per 1,000 calls and get about nine in ten right.
- **Calls that apply rules** (dates, limits, policies): a reasoning model that doesn't overthink. gpt-oss-120b, Ling 3.0 Flash and Laguna XS 2.1 got 97% to 99% for under ten cents per 1,000 calls.
- **On your own computer** there's no per-call bill, but every one of those thinking tokens is time you wait. A model that writes 2,000 tokens per answer is much slower than one that writes 80, on any hardware.

## How we measured

Costs are what OpenRouter billed us in October 2026, at the providers it routed to. We prefer providers that serve full or 8-bit precision, which aren't always the cheapest, so you may find lower prices. Token counts are as the provider reported them, and different models split text into tokens differently. One run per question, default settings. We don't measure speed. More on [how we test](/best-local-llms/methodology/).
