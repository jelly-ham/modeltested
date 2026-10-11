---
title: "We made our document test harder. Here's what changed"
dek: "Most models used to ace it. Now only a handful do, and the rankings moved a lot."
date: 2026-10-11
category: News
tags: [News, Local LLMs]
cover:
  label: "Document test · median score"
  compare:
    - { label: "Old test", value: 97 }
    - { label: "New test", value: 54 }
---

Our "reading documents" test asks a model to pull specific facts out of everyday paperwork and give them back in a fixed format. It's one of the most common things people actually use AI for.

## The old test was too easy

In the first version, the model mostly had to find a value and copy it. That turned out to be easy: 23 of the 31 models we tested scored 93 or higher, and the middle score was 97. When almost everyone gets an A, the test can't tell you which model to pick.

## What's different now

The new questions use realistic documents where most answers can't simply be copied:

- **Corrections.** An expense claim where the manager rejects one item and the employee fixes another amount two emails later.
- **Things to leave out.** A support ticket where one of the orders turns out to be cancelled.
- **A bit of math.** Totals after currency conversion, what you owe on an insurance claim, a paycheck after taxes.
- **Dates and time zones.** A deadline counted in business hours, or a flight's length across time zones.

Every answer in our answer key is calculated and checked by a script, so a correct model never loses points to a typo on our side.

## The results

Only 8 of 35 models now score 93 or higher, and the middle score dropped to 54. Some models that looked equal before are now far apart. The biggest mover was [Gemma 4 31B](/models/gemma-4-31b-it/): it still writes excellent code, but its document score fell from 99 to 72, taking it from first place to seventh.

See the updated [rankings](/best-local-llms/), or read [how we test](/best-local-llms/methodology/) for the full details.
