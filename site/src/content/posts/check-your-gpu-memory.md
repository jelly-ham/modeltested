---
title: "How to check how much memory your graphics card or Mac has"
dek: "The one number that decides which local models you can run, and where to find it on Windows, Mac and Linux."
date: 2026-10-10
category: Guides
tags: [Guides, Local LLMs, Mac]
cover:
  label: "The number that matters"
  big: "16 GB?"
---

Before you download a local model, you need one number: how much memory your graphics card has, or how much memory your Mac has. That number decides which models will fit.

## On Windows

1. Press Ctrl + Shift + Esc to open Task Manager.
2. Click the Performance tab.
3. Click GPU in the list on the left.
4. Look for "Dedicated GPU memory". That's your graphics card's memory.

If you see more than one GPU, use the one with the most dedicated memory. "Shared GPU memory" is normal computer memory and is much slower for running models.

## On a Mac

1. Click the Apple menu in the top-left corner.
2. Choose About This Mac.
3. The number next to Memory is what you need.

Apple Silicon Macs (M1 and later) share this memory between the processor and the graphics, which is why a Mac with lots of memory can run big models. By default macOS lets the graphics side use about two thirds of it on smaller Macs and about three quarters on bigger ones, and our rankings take that into account.

## On Linux with an NVIDIA card

Open a terminal and run:

```
nvidia-smi
```

The memory column shows your card's total memory in MiB. A number around 16000 means a 16 GB card, around 8000 means 8 GB.

## What to do next

Once you know your number, open our [rankings](/best-local-llms/) and find your memory size. We list the best model that fits and which version to download.
