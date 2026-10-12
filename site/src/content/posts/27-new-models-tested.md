---
title: "We tested 27 new open models, up to 127B. A 27B one still wins"
dek: "gpt-oss-120b and Meta's overlooked Muse Glimmer 30B jump to #2 and #3. Llama 4 Scout and Llama 3.3 70B land near the bottom. And a 27B model now fits a 16 GB Mac."
date: 2026-10-12
category: News
tags: [News, Local LLMs, Mac]
cover:
  label: "Overall score · out of 100"
  compare:
    - { label: "Qwen3.6 27B", value: 97 }
    - { label: "gpt-oss-120b", value: 96 }
    - { label: "Llama 3.3 70B", value: 46 }
    - { label: "Llama 4 Scout", value: 34 }
---

This week we added 27 open models to our tests. Most are big: until now we stopped at about 40 billion parameters, the most a single graphics card handles. But 96 GB and 128 GB Macs, and 128 GB "AI PCs" like AMD Strix Halo and NVIDIA DGX Spark, can now hold models of 70B to 130B, so we raised the limit. We also found a few newer mid-size models our automatic search had missed.

Same tests as always: [real coding jobs we run, documents to read, and hard tasks](/best-local-llms/methodology/). Here's what changed on the [leaderboard](/best-local-llms/).

## The short version

- **Bigger didn't win.** [Qwen3.6 27B](/models/qwen3-6-27b/) is still #1 (97 out of 100). None of the 21 new models above 40B beat it.
- **[gpt-oss-120b](/models/gpt-oss-120b/) is the best big model: #2, 96.** It needs about 63 GB, so a 96 GB Mac.
- **[Muse Glimmer 30B](/models/muse-glimmer-30b/) is #3 (94).** It's an open model Meta released in August, and it runs on a 24 GB graphics card or a 32 GB Mac.
- **Several well-known big models disappointed.** [Llama 3.3 70B](/models/llama-3-3-70b-instruct/) scored 46, [Llama 4 Scout](/models/llama-4-scout/) 34.
- **[Ternary Bonsai 2 27B](/models/ternary-bonsai-2-27b/) scored 82 in about 10 GB**, enough for a 16 GB Mac, where it's now the best model we've tested.

## The winners

| Model | Score | Coding jobs solved | Hard tasks | Memory needed |
|---|---|---|---|---|
| [Qwen3.6 27B](/models/qwen3-6-27b/) (unchanged #1) | 97 | 29 of 30 | 91 | 20 GB (Q4) |
| [gpt-oss-120b](/models/gpt-oss-120b/) | 96 | 28 of 30 | 94 | 63 GB |
| [Muse Glimmer 30B](/models/muse-glimmer-30b/) | 94 | 27 of 30 | 89 | 19 GB (Q4) |
| [Ling 3.0 Flash](/models/ling-3-0-flash/) | 94 | 28 of 30 | 91 | 84 GB (Q4) |
| [GLM 4.5V](/models/glm-4-5v/) | 93 | 26 of 30 | 89 | 67 GB (Q4) |

**gpt-oss-120b** is the one to get if you have a 96 GB or 128 GB machine and want something other than Qwen. It scored highest of everyone on our hard tasks (94), it comes in a single standard version (no picking between Q4 and Q8), and it never ran out of thinking room on our coding or document tasks.

**Muse Glimmer 30B** is the surprise. Meta released it in August outside the Llama name, so our automatic search, which looked for Meta models under the Llama account, missed it for two months. On the same hardware as Qwen3.6 27B it's 2.5 points behind, and its document score (98) is higher.

## The disappointments

| Model | Size | Score | Coding jobs solved |
|---|---|---|---|
| [Llama 4 Scout](/models/llama-4-scout/) | 109B | 34 | 9 of 30 |
| [Llama 3.3 70B](/models/llama-3-3-70b-instruct/) | 71B | 46 | 14 of 30 |
| [Mistral Small 4](/models/mistral-small-2603/) | 119B | 51 | 16 of 30 |
| [Devstral 2](/models/devstral-2512/) | 125B | 53 | 16 of 30 |
| [Qwen3 Coder Next](/models/qwen3-coder-next/) | 80B | 57 | 19 of 30 |

Llama 4 Scout needs about 68 GB at Q4 and scored lower than four of the 8B and 9B models we tested. Devstral 2 and Qwen3 Coder Next are sold as coding models but solved barely half of our coding jobs. Their marketing is built on long agent tasks, which we don't test, so they may do better there. For the self-contained programming jobs in our test, Qwen3.6 27B solves nearly twice as many in a fraction of the memory.

## A 27B model on a 16 GB Mac

[Ternary Bonsai 2 27B](/models/ternary-bonsai-2-27b/) is built from Qwen3.8 27B, but each weight is stored as -1, 0 or +1 instead of a full number. That shrinks the download to about 10 GB. It scored 82, a big step down from the full Qwen models (88 to 97), but higher than anything else that fits a [16 GB Mac](/hardware/mac-16gb/) or a [12 GB graphics card](/hardware/12gb-gpu/). It's distributed as a GGUF file in llama.cpp's ternary format; check that your app supports it before you download.

## Best model for each big machine

| Your computer | Best model | Runner-up |
|---|---|---|
| [Mac with 96 GB](/hardware/mac-96gb/) | Qwen3.6 27B (Q8) | gpt-oss-120b |
| [Mac with 128 GB](/hardware/mac-128gb/), Strix Halo, DGX Spark | Qwen3.6 27B (Q8) | gpt-oss-120b |
| [Mac with 64 GB](/hardware/mac-64gb/) | Qwen3.6 27B (Q8) | Muse Glimmer 30B (Q8) |

With 96 GB or more you can run gpt-oss-120b, but our top pick is still Qwen3.6 27B at full 8-bit quality. Keep both if you have the room: gpt-oss-120b was stronger on our hard tasks.

The full list, including the models that only just missed these tables, is on the [leaderboard](/best-local-llms/). Every score updates automatically when we add questions or models.
