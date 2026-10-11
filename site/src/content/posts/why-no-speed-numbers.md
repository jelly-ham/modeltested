---
title: "Why we don't publish speed numbers"
dek: "How fast a model runs depends on your exact computer and app, so any number we gave would be wrong for most people."
date: 2026-10-10
category: News
tags: [News, Local LLMs]
cover:
  label: "Tokens per second"
  big: "it depends"
---

Most model reviews include a speed number, usually "tokens per second". We leave it out on purpose.

## Speed depends on things we can't see

How fast a local model answers depends on your graphics card or Mac chip, how much memory it has and how fast that memory is, which app you use (Ollama, LM Studio, llama.cpp and others all behave differently), which version of the model you downloaded, how long your conversation is, and the app's settings. Change any one of those and the number changes, often a lot.

So a single speed figure from our test machine would be precise, and wrong for almost everyone reading it.

## What we measure instead

- **How good the answers are.** Every model answers the same questions, and we check the answers: code has to run, numbers have to match.
- **Whether it fits on your computer.** For each model we work out how much memory each version needs, and which graphics cards and Macs can hold it.

If a model fits comfortably in your memory, it will usually run at a usable speed. If it only just fits, expect it to be slow. Our [rankings](/best-local-llms/) only recommend models that fit with room to spare.
