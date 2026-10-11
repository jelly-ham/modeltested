---
title: "Q4 or Q8: which version of a model should you download?"
dek: "What the letters mean, how much quality you give up, and how to pick the right one for your computer."
date: 2026-10-10
category: Guides
tags: [Guides, Local LLMs]
cover:
  label: "Same model, two sizes"
  big: "Q4 / Q8"
---

When you look up a model in Ollama, LM Studio or on Hugging Face, you'll usually find it in several versions with names like Q4, Q5, Q6 and Q8. They're all the same model. The difference is how tightly it has been squeezed to save memory.

## What the number means

The number is roughly how many bits each part of the model gets. A Q8 version stores each value with about 8 bits, and a Q4 version with about 4 bits. So a Q4 file is a bit more than half the size of a Q8 file, and needs a bit more than half the memory to run.

You'll often see extra letters after the number, like Q4_K_M. Those describe the exact squeezing method. For choosing a download you can ignore them: Q4_K_M is the common "Q4" most people use.

## How much quality do you lose?

Less than you might expect. Q8 is very close to the original model. Q5 and Q6 lose a little. Q4 loses a bit more, but it's usually still the same model you'd recognize, just slightly less sharp on hard questions.

Our test scores come from the full-size version of each model, so treat them as the best that model can do. A Q4 download will usually score a little lower.

## How to choose

1. Find out how much memory you have. Our guide to [checking your graphics card or Mac memory](/posts/check-your-gpu-memory/) shows where to look.
2. Look up the model on our site. Every review has a "Can your computer run it?" table that lists the memory each version needs.
3. Pick the biggest version that fits. If Q8 fits, use it. If not, try Q6, then Q5, then Q4.

If even Q4 doesn't fit, a smaller model at Q8 will usually beat a bigger model that barely runs. Our [rankings](/best-local-llms/) already do this math for each memory size.
