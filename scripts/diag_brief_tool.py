#!/usr/bin/env python
"""Debug: call the diagnose_conversion_change tool directly on real data (no Gemini)
so we can see the actual traceback. Run: python scripts/diag_brief_tool.py
"""
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

from google.cloud import bigquery
from helios.diagnosis import load_weekly, biggest_move
from helios.llm.tools import GovernedTools

project = os.environ.get("HELIOS_PROJECT", "helios-mvp")
dataset = os.environ.get("HELIOS_MARTS_DATASET", "helios_dev")

client = bigquery.Client(project=project)
df = load_weekly(client, project, dataset)
t = GovernedTools(df, str(Path("models/semantic/semantic_layer.yaml")))

a, b = biggest_move(df)
print(f"Diagnosing {a} -> {b}\n")
try:
    res = t.diagnose_conversion_change(a, b)
    print("RAW RESULT (python):")
    print(res)
    print("\nJSON-serializable?")
    try:
        json.dumps(res, allow_nan=False)
        print("  YES — clean JSON")
    except ValueError as e:
        print(f"  NO — {e}  (likely NaN/Infinity in the result)")
except Exception:
    print("TOOL RAISED:")
    traceback.print_exc()
