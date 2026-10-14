---
title: "We tested LFM2.5-24B-A2B. The API cuts it off before it finishes"
dek: "Liquid AI's new model was right on 13 of the 14 coding jobs it finished. But the only provider stops every answer at 8,192 tokens, and on 16 jobs it was still thinking."
date: 2026-10-14
category: News
tags: [News, Local LLMs, Coding]
cover:
  label: "LFM2.5-24B-A2B · 30 coding jobs"
  compare:
    - { label: "Solved", value: 13 }
    - { label: "Cut off", value: 16 }
    - { label: "Wrong", value: 1 }
---

Liquid AI released [LFM2.5-24B-A2B](/models/lfm-2-5-24b-a2b/) this week. It has 24 billion parameters, but only about 2 billion are used for each word it writes, so it should be fast on modest hardware. Liquid calls it a reasoning model: it always thinks in private notes before it answers. We ran it through our [usual tests](/best-local-llms/methodology/).

## The short version

- **Overall: 61.7 out of 100, #30 of 67** on our [leaderboard](/best-local-llms/).
- **Decisions: 92.0.** Routing tickets, applying refund rules, spotting phishing. That's about level with Gemma 4 26B.
- **Coding: 13 of 30 jobs solved.** That number is misleading, though. Of the 14 jobs it finished, it got 13 right.
- **The problem is the API.** Liquid is the only provider on OpenRouter, and it stops every answer at 8,192 tokens, thinking included. We ask every model for up to 32,768. Liquid's own benchmarks also used 32,768.

## What happened on coding

On 16 of 30 coding jobs, the model was still thinking when the provider cut it off at 8,192 tokens, so it never wrote any code. We count those as wrong, the same as for every other model. The same thing happened on 4 of our 24 document tasks.

When it did finish, it was good: 13 of 14 coding jobs correct, and 96 out of 100 on the document tasks it finished. But it thinks a lot even then. Its finished answers were a median of about 2,900 tokens, and some ran past 7,000. Given more room, the cut-off jobs might well have finished too. We can't tell how many it would have got right, so we haven't guessed.

| | Coding jobs | Document tasks | Decision situations |
|---|---|---|---|
| Finished | 14 of 30 | 20 of 24 | 55 of 56 |
| Right when finished | 13 of 14 | 96 out of 100 | 94 out of 100 |
| Final score | 43 | 80 | 92 |

## Should you run it?

At Q4 it needs about 16 GB of memory, so it doesn't fit a [16 GB Mac](/hardware/mac-16gb/). It fits a [24 GB Mac](/hardware/mac-24gb/) at Q4 or a [24 GB graphics card](/hardware/24gb-gpu/) at Q6.

If you run it yourself, set the output limit well above 8,192 tokens. Most apps let you change it (in llama.cpp it's `-n`, in Ollama `num_predict`), and Liquid's model card recommends a temperature of 0.1. Expect long thinking: with only 2 billion active parameters each token is cheap, but you'll still be waiting for thousands of them.

For now, in the same memory, [gpt-oss-20b](/models/gpt-oss-20b/) (88.4, about 12 GB) is the safer choice. Liquid built this model for agents that call tools, which we don't test, so it may do better there.

We'll re-test if a provider offers a higher output limit. For how we grade, see [how we test](/best-local-llms/methodology/).
