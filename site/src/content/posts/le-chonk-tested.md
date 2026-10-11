---
title: "We tested Mistral Large 4 (\"Le Chonk\"). It's brilliant when it stops thinking"
dek: "Every program it finished was correct, and it beat every local model at reading documents. But on 12 of 30 coding jobs it never gave an answer at all."
date: 2026-10-11
category: News
tags: [News, Mistral, Coding]
cover:
  label: "Le Chonk · coding jobs"
  compare:
    - { label: "Solved", value: 18 }
    - { label: "Never answered", value: 12 }
---

Mistral released Mistral Large 4 this week, nicknamed "Le Chonk". It has about a trillion parameters, so you won't be running it at home: it needs hundreds of gigabytes of memory. That's why it isn't on our [leaderboard](/best-local-llms/), which is only for models you can run yourself. We were curious anyway, so we gave it the same questions and the same grading. Here's what happened.

## The short version

- **Reading documents: 99.7 out of 100.** No local model we've tested scores that high. It handled corrections buried in email threads, cancelled orders and the math on insurance claims almost perfectly.
- **Coding: 18 of 30 jobs solved.** Every program it finished passed our tests. The other 12 were left blank.
- **Decisions: 99% right.** Routing tickets, spotting phishing, applying a refund policy: almost no mistakes.

## What went wrong with coding

Le Chonk is a "thinking" model: it works through a problem in private notes before it writes the answer. We give every model room for about 25,000 words of thinking plus answer. On 12 coding jobs, Le Chonk used all of it and never got to the answer.

We read its notes on the public questions. The code was usually done early. Then it kept checking, and couldn't stop:

- On a job that reads time durations like "1h 30m", it went through every unusual space character it could think of ("what about a form feed? a non-breaking space? the Mongolian vowel separator?"), one after another, until it ran out of room.
- On a job that adds up customer payments, it listed numbers it would accept: "5,000", "5,000,000", "5,000,000,000"… adding a group of zeros each time.

This happened on easy jobs as well as hard ones, and it happened again when we ran those questions a second time. We also tried a lower "reasoning effort" setting; it didn't fix it. Our final results use that setting.

## Should you care?

If you use Le Chonk through an app or an API, this is the kind of problem you'd notice as a request that hangs for minutes and then returns nothing, and you'd still pay for all of that thinking. For document work it's excellent. For coding, a local model like [Qwen3.6 27B](/models/qwen3-6-27b/) solved 29 of the same 30 jobs and runs on your own computer for free.

We'll re-test when Mistral updates the model. For how we grade, see [how we test](/best-local-llms/methodology/).
