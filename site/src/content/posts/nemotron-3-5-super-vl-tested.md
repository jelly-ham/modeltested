---
title: "Nemotron 3.5 Super VL tested: NVIDIA's 120B jumps 11 points to #3"
dek: "The new Nemotron solved 28 of 30 coding jobs, up from 21 for Nemotron 3 Super, and now sits just behind Qwen3.6 27B and gpt-oss-120b. You'll need a 128 GB Mac or a multi-GPU rig to run it."
date: 2026-11-13
category: News
tags: [News, Local LLMs, Nemotron, Coding]
cover:
  label: "Overall score"
  compare:
    - { label: "Nemotron 3 Super", value: 84.8 }
    - { label: "Nemotron 3.5 Super VL", value: 95.9 }
    - { label: "gpt-oss-120b", value: 96.2 }
---

NVIDIA's [Nemotron 3.5 Super VL](/models/nemotron-3-5-super-vl/) is a 120B mixture-of-experts model with 12B parameters active per token, the same shape as [Nemotron 3 Super](/models/nemotron-3-super-120b-a12b/). The "VL" means it also reads images, documents, screenshots and video; we only test text. The weights are free to download under the OpenMDW license.

We ran it through OpenRouter on the same tasks as every other model: real coding jobs checked by running hidden tests, and pulling facts out of messy business documents. It scored 95.9 out of 100, #3 of the 70 models we've tested.

## The short version

| | Nemotron 3 Super | Nemotron 3.5 Super VL |
|---|---|---|
| Overall | 84.8 | **95.9** |
| Coding jobs solved | 21 of 30 | **28 of 30** |
| Reading documents | **99.7** | 98.5 |
| Hard tasks | 83.3 | **94.4** |
| Decisions (separate test) | 93.8 | **99.1** |
| Rank | #14 | **#3** of 70 |

The whole jump is coding and the hard tasks. Nemotron 3 Super was already excellent at reading documents and stays there; the new one went from middling at code to near the top.

## How it compares with the best

| Model | Overall | Coding | Documents | Hard | Memory at Q4 |
|---|---|---|---|---|---|
| [Qwen3.6 27B](/models/qwen3-6-27b/) | 96.7 | 96.7 | 96.7 | 90.6 | about 20 GB |
| [gpt-oss-120b](/models/gpt-oss-120b/) | 96.2 | 93.3 | 99.2 | 94.4 | about 63 GB* |
| **Nemotron 3.5 Super VL** | 95.9 | 93.3 | 98.5 | 94.4 | about 78 GB |

\*gpt-oss-120b ships in its own 4-bit format, MXFP4.

On scores it's level with gpt-oss-120b: the same coding result, the same hard-task score, and less than a point behind overall. [Qwen3.6 27B](/models/qwen3-6-27b/) is still #1 and needs a quarter of the memory.

## What you need to run it

At Q4, the smallest version worth downloading, Nemotron 3.5 Super VL needs about 78 GB with an 8k-token context. That's a [Mac with 128 GB](/hardware/mac-128gb/), or several graphics cards; no single consumer card has that much memory. A 96 GB Mac falls just short, because macOS keeps part of the memory for itself.

GGUF versions are already on Hugging Face from LM Studio, Unsloth and ggml-org, so it runs in LM Studio and llama.cpp. See [Q4 or Q8](/posts/q4-vs-q8/) for which version to pick.

If you have the memory, gpt-oss-120b gets the same results in less of it (about 63 GB, so it fits a 96 GB Mac) and is cheaper through an API: about $0.35 per 1,000 tasks on our test, against $2.51 for Nemotron. Two of Nemotron's 54 answers hit our token limit before finishing.

## Who should use it

If you want one model for both text and images, and you have a 128 GB Mac or a multi-GPU machine, it's well worth trying; just note that our scores cover text only. For text alone, gpt-oss-120b or Qwen3.6 27B get you the same results with less memory.

Full scores, memory at every quantization and sample answers are on the [Nemotron 3.5 Super VL page](/models/nemotron-3-5-super-vl/). For the full leaderboard, see [the best local LLMs](/best-local-llms/).
