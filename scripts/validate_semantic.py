#!/usr/bin/env python
"""validate_semantic.py — referential-integrity check for the Helios semantic registry.

Loads models/semantic/semantic_layer.yaml and proves every metric's references
resolve WITHIN the registry (0 dangling refs). This is the data-independent half of
M5 — it needs no BigQuery. (The against-real-marts column check is layered on later
once the marts exist.)

The registry uses DESCRIPTIVE field names (metric_name / sql_definition / aggregation_method
/ dimensions_supported), NOT the short adapter names (name/sql/agg/dimensions). This reads
the descriptive names directly.

Exit 0 = PASS (no dangling refs); exit 1 = FAIL.
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

REGISTRY = Path(__file__).resolve().parents[1] / "models" / "semantic" / "semantic_layer.yaml"


def main() -> int:
    if not REGISTRY.exists():
        print(f"FAIL: registry not found at {REGISTRY}")
        return 1

    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    grains = set((data.get("grains") or {}).keys())
    entities = {e["entity_name"] for e in (data.get("entities") or [])}
    dimensions = {d["dimension_name"] for d in (data.get("dimensions") or [])}
    metrics = data.get("metrics") or []
    metric_names = {m["metric_name"] for m in metrics}

    errors: list[str] = []
    warnings: list[str] = []

    for m in metrics:
        name = m.get("metric_name", "<unnamed>")

        grain = m.get("grain")
        if grain and grain not in grains:
            errors.append(f"[{name}] grain '{grain}' not in grains {sorted(grains)}")

        entity = m.get("entity")
        if entity and entity not in entities:
            errors.append(f"[{name}] entity '{entity}' not in entities")

        for ref_field in ("numerator", "denominator"):
            ref = m.get(ref_field)
            if ref and ref not in metric_names:
                errors.append(f"[{name}] {ref_field} '{ref}' is not a defined metric")

        for dim in (m.get("dimensions_supported") or []):
            if dim not in dimensions:
                errors.append(f"[{name}] dimension '{dim}' not in dimensions section")

        rc = m.get("root_cause") or {}
        for rc_field in ("upstream_drivers", "downstream_impacts"):
            for ref in (rc.get(rc_field) or []):
                if ref not in metric_names:
                    warnings.append(f"[{name}] root_cause.{rc_field} '{ref}' is not a defined metric")

    print(f"Registry: {REGISTRY.name}")
    print(f"  metrics={len(metrics)}  grains={len(grains)}  entities={len(entities)}  dimensions={len(dimensions)}")
    if warnings:
        print(f"\n  {len(warnings)} warning(s) (non-blocking, root_cause hints):")
        for w in warnings[:20]:
            print(f"    WARN {w}")
        if len(warnings) > 20:
            print(f"    ... +{len(warnings) - 20} more")

    if errors:
        print(f"\nFAIL: {len(errors)} dangling reference(s):")
        for e in errors:
            print(f"    ERROR {e}")
        return 1

    print("\nPASS - 0 dangling refs. Every grain/entity/numerator/denominator/dimension resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
