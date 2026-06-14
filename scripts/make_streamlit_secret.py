#!/usr/bin/env python
"""Convert the GCP service-account JSON key into Streamlit's TOML secret format.

Reads C:\\Users\\<you>\\helios-dashboard-key.json (outside the repo) and prints a
[gcp_service_account] block to paste into Streamlit Cloud -> app -> Settings -> Secrets.

The key file and this output are SECRET — do NOT commit them or paste them in chat.
Run:  python scripts/make_streamlit_secret.py
"""
import json
from pathlib import Path

key_path = Path.home() / "helios-dashboard-key.json"
if not key_path.exists():
    raise SystemExit(f"Key not found at {key_path} — re-run the `gcloud ... keys create` step.")

d = json.loads(key_path.read_text(encoding="utf-8"))

print("\n# ---- copy everything BELOW this line into Streamlit's Secrets box ----\n")
print("[gcp_service_account]")
for k, v in d.items():
    if isinstance(v, str):
        esc = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        print(f'{k} = "{esc}"')
    else:
        print(f"{k} = {json.dumps(v)}")
print("\n# ---- copy everything ABOVE this line ----\n")
