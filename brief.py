#!/usr/bin/env python
"""brief.py — Helios v1: the GROUNDED LLM Decision Brief (no hand-written SQL, no in-prose math).

An LLM (Gemini) diagnoses the funnel by CALLING governed tools (the deterministic mix/rate
engine + the metric registry) and writes an executive Decision Brief. Every number is a
tool output; the model never computes anything itself.

Setup (one-time):
    pip install google-genai
    set a Gemini key:  $env:GEMINI_API_KEY = "AIza..."   (PowerShell)
    (get a free key at https://aistudio.google.com/apikey)

Usage:
    python brief.py
    python brief.py --project helios-mvp --dataset helios_dev --model gemini-2.5-flash
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent / "models" / "semantic" / "semantic_layer.yaml"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_MARTS_DATASET", "helios_dev"))
    ap.add_argument("--model", default=os.environ.get("HELIOS_GEMINI_MODEL", "gemini-2.5-flash"))
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        sys.exit("ERROR: set GEMINI_API_KEY (PowerShell: $env:GEMINI_API_KEY = \"AIza...\").\n"
                 "Get a free key at https://aistudio.google.com/apikey")

    from google.cloud import bigquery
    from helios.diagnosis import load_weekly
    from helios.llm.brief import generate_decision_brief

    print(f"Loading funnel data from {args.project}.{args.dataset} …")
    client = bigquery.Client(project=args.project)
    df = load_weekly(client, args.project, args.dataset)

    print(f"Generating grounded Decision Brief with {args.model} …\n")
    result = generate_decision_brief(df, str(REGISTRY), api_key, args.model)

    print("=" * 70)
    print(result.text)
    print("=" * 70)
    print("\nGROUNDING — governed tools the model called (every number traces to these):")
    for c in result.tool_calls:
        print(f"  • {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
