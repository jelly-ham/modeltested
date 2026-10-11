---
title: "How to run a local LLM with Ollama"
dek: "Install one app, type one command, and you're chatting with an AI model on your own computer. No account needed."
date: 2026-10-10
category: Guides
tags: [Guides, Local LLMs, Ollama]
cover:
  label: "One command"
  big: "ollama run"
---

Ollama is a free app that downloads AI models and runs them on your computer. It works on Windows, Mac and Linux, and it's the quickest way to try a local model.

## 1. Install Ollama

Download it from [ollama.com](https://ollama.com) and install it like any other app. On Linux the site gives you a one-line install command.

## 2. Pick a model that fits

Check how much memory you have (here's [how to find it](/posts/check-your-gpu-memory/)), then find a model that fits in our [rankings](/best-local-llms/). Every model review on this site shows the Ollama command when one is available.

## 3. Run it

Open a terminal (on Windows, PowerShell works) and type `ollama run` followed by the model's name. For example:

```
ollama run gpt-oss:20b
```

The first time, Ollama downloads the model, which can take a while: these files are several gigabytes. After that it starts in seconds. Type a question and press Enter. Type `/bye` to quit.

## Tips

- **Too slow, or it won't load?** The model is probably too big for your memory. Try a smaller model, or a smaller version of the same one (see [Q4 or Q8](/posts/q4-vs-q8/)).
- **Prefer a normal chat window?** LM Studio is a free app with a regular chat interface that can run the same models.
- **Your data stays put.** Everything runs on your machine, so nothing you type is sent to a company's servers.
