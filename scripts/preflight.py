#!/usr/bin/env python
"""preflight.py — "where am I?" checker for the Helios MVP setup.

Run anytime:  python scripts/preflight.py
It prints a checklist of every setup step (done / not yet) and the next action.
Safe to run before anything is installed — missing tools are reported, not crashed on.
"""
from __future__ import annotations
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


def _importable(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False

ROOT = Path(__file__).resolve().parents[1]
OK, NO, WARN = "[ OK ]", "[ -- ]", "[WARN]"
results: list[tuple[str, str, str]] = []


def add(status, label, hint=""):
    results.append((status, label, hint))


def run(cmd) -> tuple[bool, str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return out.returncode == 0, (out.stdout + out.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return False, str(e)


# 1. Python version of the CURRENT interpreter (dbt 1.8 supports 3.9–3.12)
v = sys.version_info
if v.major == 3 and 9 <= v.minor <= 12:
    add(OK, f"Python interpreter is dbt-compatible ({v.major}.{v.minor}.{v.micro})")
else:
    add(WARN, f"Running under Python {v.major}.{v.minor} (dbt 1.8 needs 3.9-3.12)",
        "Activate the 3.12 venv: .venv\\Scripts\\activate  (create with: py -3.12 -m venv .venv)")

# 2. In a venv?
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
add(OK if in_venv else NO, "Virtual environment active",
    "" if in_venv else "Run: .venv\\Scripts\\activate")

# 3. gcloud present
if shutil.which("gcloud"):
    add(OK, "gcloud SDK installed")
else:
    add(NO, "gcloud SDK installed", "Install: https://cloud.google.com/sdk/docs/install")

# 4. dbt importable
try:
    import dbt.version  # noqa: F401
    add(OK, "dbt installed (pip)")
except Exception:
    add(NO, "dbt installed", "Run: pip install -r requirements.txt  (inside the 3.11 venv)")

# 5. Python deps for the math engine
missing = [m for m in ("scipy", "yaml", "pandas") if not _importable(m)]
add(OK if not missing else NO, "Math deps (scipy, pyyaml, pandas)",
    "" if not missing else f"Missing {missing}; run: pip install -r requirements.txt")

# 6. google-cloud-bigquery
add(OK if _importable("google.cloud.bigquery") else NO, "google-cloud-bigquery installed",
    "" if _importable("google.cloud.bigquery") else "Run: pip install -r requirements.txt")

# 7. profiles.yml project edited
prof = (ROOT / "profiles.yml")
if prof.exists():
    txt = prof.read_text(encoding="utf-8")
    if "helios-analytics" in txt:
        add(NO, "profiles.yml points at YOUR project",
            "Edit profiles.yml: replace 'helios-analytics' with your GCP project id (2 lines)")
    else:
        add(OK, "profiles.yml project id edited")
else:
    add(NO, "profiles.yml present", "Missing profiles.yml in repo root")

# 8. ADC credentials available
ok_adc = False
try:
    import google.auth  # noqa
    creds, _ = google.auth.default()
    ok_adc = creds is not None
except Exception:
    ok_adc = False
add(OK if ok_adc else NO, "BigQuery login (ADC) present",
    "" if ok_adc else "Run: gcloud auth application-default login")

# 9. dbt can connect (only if dbt + profile ready)
if shutil.which("dbt") or _importable("dbt"):
    ok, _out = run(["dbt", "debug", "--profiles-dir", str(ROOT)])
    add(OK if ok else NO, "dbt debug passes (BigQuery reachable)",
        "" if ok else "Run: dbt debug --profiles-dir .   (and fix what it reports)")
else:
    add(NO, "dbt debug passes (BigQuery reachable)", "Install dbt first")

# --- report ---
print("\nHELIOS MVP - preflight checklist\n" + "-" * 48)
for status, label, hint in results:
    print(f"  {status}  {label}")
    if status != OK and hint:
        print(f"          -> {hint}")
print("-" * 48)
done = sum(1 for s, _, _ in results if s == OK)
print(f"  {done}/{len(results)} ready.")
nxt = next((h for s, _, h in results if s == NO and h), None)
if nxt:
    print(f"  NEXT: {nxt}")
else:
    print("  All green — run: dbt build --profiles-dir .  then  python diagnose.py")
