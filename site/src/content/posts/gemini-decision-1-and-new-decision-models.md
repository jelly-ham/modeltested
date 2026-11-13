---
title: "Gemini Decision 1 vs GPT-6 Luna: Google's decision model wins by 6 points"
dek: "Gemini Decision 1 lands at #2 of 30 with the best calibration we've measured. Plus six more new decision models, including three open-weight ones from Baseten built on Qwen3.5."
date: 2026-11-13
category: News
tags: [News, Decision models, Rankings]
cover:
  label: "Decision accuracy"
  compare:
    - { label: "Gemini Decision 1", value: 95.5 }
    - { label: "Mammoth 1", value: 92.0 }
    - { label: "GPT-6 Luna Decisions", value: 89.3 }
---

Seven new decision models showed up on OpenRouter between October 28 and November 11, and the daily run tested each one on the same 56 situations as every other [decision model](/best-decision-models/): routing support tickets, applying refund and expense rules, spotting phishing, triaging incidents. 19 of the 56 are hard ones, with the catch buried in the details.

The headline is Google's. Gemini Decision 1 is the first decision model from a big lab that competes with the best of the specialists, and it's well ahead of OpenAI's.

## The short version

| Model | Accuracy | Hard ones | Rank (of 30) | Cost per 1,000 calls | Compared with |
|---|---|---|---|---|---|
| [Gemini Decision 1](/decision-models/gemini-decision-1/) | 95.5 | 92.1 | #2 | $0.03 | GPT-6 Luna Decisions: 89.3 |
| [Mammoth 1](/decision-models/mammoth-1/) (open, 27B) | 92.0 | 86.8 | #7 | $0.03 | its base, Qwen3.5-27B: 100 |
| [Drex Max Finance](/decision-models/drex-max-finance/) | 92.0 | 89.5 | #8 | $0.01 | Drex Max: 93.8 |
| [Reflex](/decision-models/reflex/) | 92.0 | 92.1 | #9 | $0.02 | (new) |
| [Elephant 1](/decision-models/elephant-1/) (open, 9B) | 91.1 | 84.2 | #14 | $0.01 | its base, Qwen3.5-9B: 97.3 |
| [d1.1](/decision-models/d1-1/) | 88.4 | 73.7 | #19 | under $0.01 | d1: 86.6 |
| [Joey 1](/decision-models/joey-1/) (open, 2B) | 80.4 | 65.8 | #29 | under $0.01 | (new) |

Accuracy is out of 100. Ties share a score but are listed in the order on our [rankings page](/best-decision-models/).

## Gemini Decision 1 vs GPT-6 Luna Decisions

| | Gemini Decision 1 | [GPT-6 Luna Decisions](/decision-models/gpt-6-luna-decisions/) |
|---|---|---|
| Accuracy | **95.5** | 89.3 |
| Hard ones | **92.1** | 78.9 |
| Hard ones fully right | **17 of 19** | 13 of 19 |
| Situations with a mistake | **4 of 56** | 10 of 56 |
| Calibration | **97.0**, best of 30 | 94.5 |
| Cost per 1,000 calls | **$0.03** | $0.04 |
| Rank among decision models | **#2** | #18 |

Both charge the same $0.10 per million input tokens and nothing for output, so the price difference comes down to how many tokens each one bills for the same question. Gemini averaged about 250 input tokens per call on our public questions, Luna about 420, so Gemini is cheaper as well as better.

Gemini ties [Solar Decide](/decision-models/solar-decide/) on accuracy (95.5) and is behind only [Span-02](/decision-models/span-02/) (96.4), which is still cheaper at under a cent per 1,000 calls. Where Gemini stands out is calibration: when it says it's 80% sure, it's right about as often as that, more consistently than any other decision model we've tested. If you act on the probabilities, not just the top answer, that matters.

We covered Luna's misses in detail in [our GPT-6 Luna Decisions review](/posts/gpt-6-luna-decisions-tested/). Gemini got something wrong on four situations, two of them hard ones.

## Baseten's open trio: Mammoth, Elephant and Joey

Base Labs, Baseten's research team, released three decision models with open weights under the MIT license, each a fine-tune of a Qwen3.5 model:

| Model | Built on | Accuracy | Hard ones | Cost per 1,000 calls |
|---|---|---|---|---|
| Mammoth 1 | Qwen3.5-27B | 92.0 | 86.8 | $0.03 |
| Elephant 1 | Qwen3.5-9B | 91.1 | 84.2 | $0.01 |
| Joey 1 | Qwen3.5-2B | 80.4 | 65.8 | under $0.01 |

Mammoth 1 is now the best decision model you can download. It ties [Drex v1.5](/decision-models/drex-v1-5/) on accuracy (92.0) and beats it on the hard ones (86.8 against 84.2) and on calibration.

The interesting comparison is with the models they're built on. Given the same situations as regular LLMs, [Qwen3.5-27B](/models/qwen3-5-27b/) gets every one right (100) and [Qwen3.5-9B](/models/qwen3-5-9b/) gets 97.3. But they think before answering, and that costs: $5.92 and $0.58 per 1,000 calls through OpenRouter. Mammoth and Elephant answer in one pass for $0.03 and $0.01. So the fine-tune gives up 6 to 8 points of accuracy to be roughly 60 to 220 times cheaper per call. Whether that's a good trade depends on how much a wrong call costs you.

Joey 1, at 2B, is #29 of 30. It's very cheap and small enough to run almost anywhere, but it got 17 of the 56 situations at least partly wrong.

## Reflex: strong on the hard ones

Morph's Reflex scored 92.0 overall but 92.1 on the hard situations, which is unusual: most models drop several points there. Only Span-02, Solar Decide, Gemini Decision 1 and Drex Max do as well or better on the hard ones. It bills more input tokens than the others (about 530 per call), but it caches the situation, so asking several questions about the same input costs less than the per-call price suggests.

## Drex Max Finance and d1.1: small changes

Nace AI's Drex Max Finance is a finance-tuned version of [Drex Max](/decision-models/drex-max/). On our mix, which is mostly not finance, it's a little worse: 92.0 against 93.8, and 89.5 against 92.1 on the hard ones. It's also about 20% cheaper per call. If your decisions are about invoices, receipts and statements, it may do better than our numbers suggest; we don't have a finance-only test.

Liquid's d1.1 improves on [d1](/decision-models/d1/), 88.4 against 86.6, with the same score on the hard ones (73.7). It's still behind Liquid's own [d1-ultra](/decision-models/d1-ultra/) (90.2), but cheaper, at well under a cent per 1,000 calls.

## Still behind regular LLMs

None of the new models changes the bigger picture: 14 regular open models are more accurate than the best decision model on the same 56 situations, and some of them are cheap to run, as we found in [what each call really costs](/posts/decision-models-cost/). Decision models win on price and simplicity, not on accuracy.

Full results, including how honest each model's confidence is, are on the [decision model rankings](/best-decision-models/). For how we grade, see [how we test](/best-local-llms/methodology/).
