# Model Tested

An open benchmark of open-weight LLMs on boring, real work: code that has to run, numbers pulled out of messy documents, and routine decisions like routing a ticket or spotting phishing. Results are at **[modeltested.com](https://modeltested.com)** and update automatically when a new open model ships.

**Current results:** [leaderboard of 65 local models](https://modeltested.com/best-local-llms/) · [decision models vs. regular LLMs](https://modeltested.com/best-decision-models/) · [tokens and cost per call](https://modeltested.com/posts/decision-models-cost/)

## How the grading works

| Test | Questions | Graded by |
|---|---|---|
| Coding | 30 (10 hard) | Running the model's code against hidden unit tests in a sandbox (Docker: no network, read-only, unprivileged) |
| Reading documents | 24 (8 hard) | Field-by-field comparison with a calculated answer key (corrections in email threads, currency conversion, business-day deadlines) |
| Decisions | 56 (19 hard) | Accuracy of the most likely option, plus Brier score for calibration |

- **Most questions are hidden.** They live in this public repo as an [age](https://age-encryption.org)-encrypted tarball (`bench/private.tar.age`); the key is a CI secret. A public sample is plaintext in `bench/public/`, and every model's raw answers to it are on the site, so you can check the grading.
- **Public vs. hidden scores are shown side by side.** A big gap is a red flag for memorization. The public files carry a canary string so training pipelines can exclude them.
- **Every model gets the same prompt and grading.** Models run through OpenRouter at full or 8-bit precision; some Q4 downloads are also run with Ollama on a Mac mini (M4, 16 GB) to show what quantization costs.
- **No speed numbers.** They depend too much on your hardware. Instead each model gets a memory estimate: which graphics card or Mac it fits on, and which quantization to download.
- **Incremental.** Each question is hashed, so a new model or an edited question only re-runs what changed. Testing a new model costs cents to a few dollars.

Known limits: one run per question with default sampling, a question bank that's still small, and cloud precision rather than your exact Q4 file. Corrections and question ideas are welcome in Issues.

## Repo layout

- **runner/** — Python (stdlib only): discovers models on OpenRouter, runs the question bank, grades answers, estimates memory needs, writes site data.
- **bench/** — question bank. `public/` is plaintext and published; the hidden set lives encrypted in `private.tar.age`.
- **results/** — per-model scores (question ids + scores only) and raw outputs for *public* questions.
- **site/** — Astro static site, deployed to Cloudflare (free plan) by GitHub Actions.

## How it works

Every day `.github/workflows/bench.yml`:

1. decrypts the hidden set with the `AGE_SECRET_KEY` secret,
2. validates the question bank (`selfcheck`),
3. adds new open-weight models up to ~130B (fits a 128 GB Mac) from allowlisted labs (`discover`),
4. runs only the missing (model, question) pairs, within a spend budget (`run`),
5. aggregates scores into `site/src/data` (`build-data`) and commits results,
6. builds the site and deploys it with Wrangler.

Model-written code runs in Docker with no network, a read-only filesystem, an unprivileged user and CPU/memory/pid limits.

## One-time setup

Repository secrets (Settings → Secrets and variables → Actions):

| Name | Value |
|---|---|
| `AGE_SECRET_KEY` | contents of `.secrets/age-key.txt` (the `AGE-SECRET-KEY-…` line) |
| `OPENROUTER_API_KEY` | OpenRouter API key (set a monthly spend limit on it) |
| `CLOUDFLARE_API_TOKEN` | token with the "Edit Cloudflare Workers" template |
| `CLOUDFLARE_ACCOUNT_ID` | your Cloudflare account id |

Repository variable `SITE_URL` = `https://modeltested.com` (optional — that's also the default in `site/astro.config.mjs`).

Also set `REPO_URL` in `site/src/lib/data.ts` to the GitHub repo.

## Local commands

```bash
python3 -m runner selfcheck                       # validate questions (needs Docker)
python3 -m runner discover --dry-run              # see which new models would be added
OPENROUTER_API_KEY=... python3 -m runner run --models qwen3-14b --budget-usd 0.5
python3 -m runner build-data
cd site && npm install && npm run dev

# pipeline smoke test without an API key (mock models answer with the answer key / garbage)
python3 -m runner run --models mock-reference,mock-broken && python3 -m runner build-data --include-test
```

## Local runs on the Mac (quantized downloads)

Models with `"status": "local"` in `bench/models.json` are run with Ollama on a Mac mini (M4, 16 GB), never in CI.
They measure what a Q4 download loses against full precision (shown on the base model's page), or fill in for a
model no OpenRouter provider serves reliably (ranked, with "(Q4, Mac)" in its name). Fields: `ollama_tag`, `quant`
(checked against Ollama after pulling), `base` (the full-precision slug), optional `max_tokens` / `num_ctx` / `think`.

One-time setup on the Mac:

```bash
brew install ollama age gh colima docker   # or Docker Desktop instead of colima + docker
colima start --cpu 2 --memory 2            # skip with Docker Desktop
gh auth login && gh repo clone jelly-ham/modeltested && cd modeltested
mkdir -p .secrets && pbpaste > .secrets/age-key.txt   # copy the AGE-SECRET-KEY line first; never commit it
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve   # leave running (halves KV-cache memory)
```

Then, whenever there's something to test:

```bash
scripts/mac-run.sh                        # all local models; or: scripts/mac-run.sh gemma-3-4b-q4-mac
```

It pulls the model, answers every missing question one at a time (Ctrl-C keeps finished answers), grades them,
commits only `results/scores`, `results/outputs` (public questions) and `bench/models.json`, and pushes; the push
triggers the workflow, which rebuilds the site.

### CLM (contrastive decision model) on the Mac

`clm-v0-1-8b` answers only the decisions suite. It needs two local servers, then `scripts/mac-run.sh clm-v0-1-8b`:

```bash
brew install llama.cpp
# 1. Qwen3-8B encoder, last-token pooling (the reference setup is vLLM on a GPU)
llama-server -hf czl/CLM-v0.1-8B-GGUF:Q8_0 --embeddings --pooling last -c 2048 -b 2048 -ub 2048 --port 8090 --alias qwen3-8b
# 2. in another terminal: the CLM heads
python3 -m venv ~/clm-venv && ~/clm-venv/bin/pip install contrastive-lm
CLM_DEVICE=cpu ~/clm-venv/bin/clm-serve --emb-url http://127.0.0.1:8090/v1/embeddings
```

Sanity check before a run (should pick "billing" with high probability):

```bash
curl -s localhost:8700/v1/systemone -H 'Content-Type: application/json' -d '{"state":"Customer: my invoice was charged twice and nobody answers the phone!","questions":{"department":{"type":"choice","instructions":"Which team should handle this?","criteria":{"billing":"Charges, invoices, refunds","technical":"Bugs and outages"}}}}'
```

## Editing the hidden question set

```bash
scripts/decrypt-private.sh        # needs .secrets/age-key.txt → plaintext in bench/private/ (gitignored)
# edit bench/private/*.json
python3 -m runner selfcheck       # every reference must pass, an empty answer must fail
scripts/encrypt-private.sh        # writes bench/private.tar.age — commit that file only
```

Changing a question's prompt, tests or answer key changes its hash, so only that question is re-run for every model.
Bump `RUNNER_VERSION` in `runner/common.py` after changing prompts or grading to re-run everything.

## Rules for a public repo

- Never commit `bench/private/` or `.secrets/` (both gitignored).
- CI logs and artifacts are public: don't add steps that print or upload hidden questions or model outputs for them.
- Don't use `pull_request_target` workflows — fork PRs must never see secrets.
- If the age key leaks, rotate it **and** retire the hidden questions (treat them as public).
