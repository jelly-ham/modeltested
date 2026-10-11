"""Run local (status "local") models through Ollama on the Mac test machine.

These are the quantized downloads people actually run (Q4 etc.), graded on the same
questions as everything else. Used to fill gaps (models no OpenRouter provider serves
reliably) and to measure how much quality a Q4 download loses against full precision.
Never run in CI: the GitHub runner has no Ollama.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from argparse import Namespace

from . import client, run
from .common import load_models, save_models

BPW = {"Q4": 4.85, "Q5": 5.69, "Q6": 6.59, "Q8": 8.5, "F16": 16.0, "BF16": 16.0}


def main(args) -> None:
    doc = load_models()
    local = [m for m in doc["models"] if m.get("status") == "local"]
    if args.models:
        wanted = set(args.models.split(","))
        unknown = wanted - {m["slug"] for m in local}
        if unknown:
            raise SystemExit(f"not local models: {sorted(unknown)} (local: {', '.join(m['slug'] for m in local)})")
        local = [m for m in local if m["slug"] in wanted]
    if not local:
        raise SystemExit('no models with status "local" in bench/models.json')

    changed, ready = False, []
    clm = [m for m in local if m.get("backend") == "clm"]
    if clm:
        try:
            with urllib.request.urlopen(client.CLM_URL + "/health", timeout=10) as r:
                ok = json.loads(r.read()).get("ok")
        except Exception as e:
            ok = False
            print(f"clm-serve is not reachable at {client.CLM_URL} ({e})", flush=True)
        if ok:
            ready += clm
        else:
            print("SKIPPED " + ", ".join(m["slug"] for m in clm) + ": start llama-server and clm-serve first (see README)", flush=True)
    local = [m for m in local if m.get("backend") != "clm"]
    if local:
        try:
            client._ollama("/api/version")
        except Exception as e:
            raise SystemExit(f"Ollama is not reachable at {client.OLLAMA} ({e}). Start the Ollama app first.")

    for m in local:
        print(f"[{m['slug']}] ollama pull {m['ollama_tag']}", flush=True)
        if subprocess.run(["ollama", "pull", m["ollama_tag"]]).returncode != 0:
            print(f"[{m['slug']}] SKIPPED: could not pull {m['ollama_tag']} (check the tag on ollama.com)", flush=True)
            continue
        ready.append(m)
        quant = client.ollama_quant(m["ollama_tag"])
        # Record what was really tested: Ollama's default tags differ in quantization between models.
        if quant and quant != m.get("quant"):
            print(f"[{m['slug']}] quantization is {quant} (models.json said {m.get('quant')}); updating", flush=True)
            m["quant"] = quant
            short = quant.split("_")[0]
            m["name"] = m["name"].replace(f"({m['name'].split('(')[-1].split(',')[0]},", f"({short},")
            m["native_quant"] = {"name": quant, "bpw": BPW.get(short, m["native_quant"]["bpw"])}
            changed = True
    if changed:
        save_models(doc)
    if not ready:
        raise SystemExit("nothing to run")

    run.main(Namespace(models=",".join(m["slug"] for m in ready), suites=args.suites, rerun=args.rerun,
                       budget_usd=float("inf"), max_minutes=args.max_minutes, concurrency=1, local=True))
    sys.stdout.flush()
