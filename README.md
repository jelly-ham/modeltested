# Model Tested

Source of [modeltested.com](https://modeltested.com): automated, task-based tests of AI models, published as a static site. The first section ranks open-weight LLMs you can run locally.

- **runner/** — Python (stdlib only): discovers models on OpenRouter, runs the question bank, grades answers, estimates memory needs, writes site data.
- **bench/** — question bank. `public/` is plaintext and published; the hidden set lives encrypted in `private.tar.age`.
- **results/** — per-model scores (question ids + scores only) and raw outputs for *public* questions.
- **site/** — Astro static site, deployed to Cloudflare (free plan) by GitHub Actions.

## How it works

Every day `.github/workflows/bench.yml`:

1. decrypts the hidden set with the `AGE_SECRET_KEY` secret,
2. validates the question bank (`selfcheck`),
3. adds new open-weight models ≤ 40B from allowlisted labs (`discover`),
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
