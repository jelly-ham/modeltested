"""Run untrusted, model-written Python in a locked-down Docker container.

All cases for one model+suite run in a single container: no network, read-only
filesystem, unprivileged user, CPU/memory/pid limits, per-case timeout.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGE = os.environ.get("SANDBOX_IMAGE", "python:3.12-slim")
CASE_TIMEOUT = 10

HARNESS = r'''
import json, subprocess, sys, os
results = {}
for name in sorted(os.listdir("/work/cases")):
    cid = name[:-3]
    try:
        p = subprocess.run([sys.executable, "-I", "/work/cases/" + name], cwd="/tmp",
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=%d)
        err = p.stderr.strip().splitlines()
        results[cid] = {"passed": p.returncode == 0, "error": err[-1][:300] if err and p.returncode else None}
    except subprocess.TimeoutExpired:
        results[cid] = {"passed": False, "error": "timeout"}
print("@@RESULTS@@" + json.dumps(results))
''' % CASE_TIMEOUT


def run_cases(cases: dict[str, str]) -> dict[str, dict]:
    """cases: case_id -> python source. Returns case_id -> {passed, error}."""
    if not cases:
        return {}
    tmp = Path(tempfile.mkdtemp(prefix="sbx-"))
    try:
        (tmp / "cases").mkdir()
        ids = {}
        for i, (cid, src) in enumerate(cases.items()):
            name = f"c{i:04d}"
            ids[name] = cid
            (tmp / "cases" / f"{name}.py").write_text(src)
        (tmp / "harness.py").write_text(HARNESS)
        for p in [tmp, tmp / "cases", *tmp.rglob("*")]:
            p.chmod(0o755 if p.is_dir() else 0o644)

        if shutil.which("docker"):
            cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "1g", "--cpus", "2",
                   "--pids-limit", "256", "--read-only", "--tmpfs", "/tmp:size=64m",
                   "--user", "65534:65534", "--security-opt", "no-new-privileges",
                   "-v", f"{tmp}:/work:ro", IMAGE, "python", "-I", "/work/harness.py"]
        elif os.environ.get("BENCH_UNSAFE_LOCAL") == "1":
            local = Path(tempfile.mkdtemp())
            harness = HARNESS.replace("/work", str(tmp)).replace('cwd="/tmp"', f'cwd="{local}"')
            (tmp / "harness.py").write_text(harness)
            cmd = ["python3", "-I", str(tmp / "harness.py")]
        else:
            raise RuntimeError("docker not found (set BENCH_UNSAFE_LOCAL=1 to run model code unsandboxed)")

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=CASE_TIMEOUT * len(cases) + 120)
        marker = [ln for ln in p.stdout.splitlines() if ln.startswith("@@RESULTS@@")]
        if not marker:
            raise RuntimeError(f"sandbox failed (exit {p.returncode}): {p.stderr[-500:]}")
        raw = json.loads(marker[-1][len("@@RESULTS@@"):])
        return {ids[k]: v for k, v in raw.items()}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
