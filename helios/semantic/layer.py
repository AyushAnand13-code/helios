"""SemanticLayer — compose governed SQL from the metric/dimension registry.

This is the structural enforcement of grounding rules G1 and G5: the only way to get
SQL is `build_query(metrics, dimensions, ...)`, which assembles a SELECT from each
metric's registered `sql_definition` and each dimension's column expression. Unknown
names, dimensions a metric doesn't support, or metrics that span different physical
grains all raise SemanticError — there is no path to free-typed SQL.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_REGISTRY = (Path(__file__).resolve().parents[2]
                    / "models" / "semantic" / "semantic_layer.yaml")

_VALID_OPS = {"=", "!=", ">", ">=", "<", "<=", "IN", "NOT IN", "BETWEEN"}


class SemanticError(Exception):
    """Raised on any governance violation: unknown metric/dimension, an unsupported
    dimension for a metric, mixed grains, or a malformed filter."""


@dataclass(frozen=True)
class Filter:
    dimension: str
    op: str
    value: object   # scalar, [lo, hi] for BETWEEN, or list for IN


class SemanticLayer:
    def __init__(self, registry_path: str | Path = DEFAULT_REGISTRY):
        reg = yaml.safe_load(Path(registry_path).read_text(encoding="utf-8"))
        self.metrics = {m["metric_name"]: m for m in (reg.get("metrics") or [])}
        self.dimensions = {d["dimension_name"]: d for d in (reg.get("dimensions") or [])}
        if not self.metrics or not self.dimensions:
            raise SemanticError(f"registry at {registry_path} has no metrics/dimensions")

    # ── lookups (G5: unknown name is a hard error) ────────────────────────────────
    def get_metric(self, name: str) -> dict:
        try:
            return self.metrics[name]
        except KeyError:
            raise SemanticError(
                f"'{name}' is not a governed metric. Known: {sorted(self.metrics)[:12]}…")

    def get_dimension(self, name: str) -> dict:
        try:
            return self.dimensions[name]
        except KeyError:
            raise SemanticError(
                f"'{name}' is not a governed dimension. Known: {sorted(self.dimensions)[:12]}…")

    def list_metrics(self) -> list[str]:
        return sorted(self.metrics)

    def list_dimensions(self) -> list[str]:
        return sorted(self.dimensions)

    # ── governed SQL composition (G1) ─────────────────────────────────────────────
    def build_query(self, metrics: list[str], dimensions: list[str] | None = None,
                    filters: list[Filter | dict] | None = None, *,
                    project: str | None = None, dataset: str = "helios_dev",
                    order_by_time: bool = True) -> str:
        """Compose a governed SELECT for `metrics` grouped by `dimensions`.

        Every metric must exist, share a single physical grain, and support every
        requested dimension; otherwise SemanticError. The returned SQL is assembled only
        from registered definitions — it is never hand-typed.
        """
        if not metrics:
            raise SemanticError("build_query requires at least one metric")
        dimensions = dimensions or []
        mdefs = [self.get_metric(m) for m in metrics]
        ddefs = [self.get_dimension(d) for d in dimensions]

        grains = {m["grain"] for m in mdefs}
        if len(grains) > 1:
            raise SemanticError(
                f"metrics span multiple grains {sorted(grains)}; one query = one grain")
        grain = grains.pop()

        for m in mdefs:
            supported = set(m.get("dimensions_supported") or [])
            for d in dimensions:
                if d not in supported:
                    raise SemanticError(
                        f"metric '{m['metric_name']}' does not support dimension '{d}'")

        select_parts = [f"{d['sql_definition']} AS {d['dimension_name']}" for d in ddefs]
        select_parts += [f"{m['sql_definition']} AS {m['metric_name']}" for m in mdefs]

        table = f"`{project}.{dataset}.{grain}`" if project else f"`{dataset}.{grain}`"
        sql = "SELECT\n  " + ",\n  ".join(select_parts) + f"\nFROM {table}"

        where = self._render_filters(filters, dimensions)
        if where:
            sql += f"\nWHERE {where}"
        if dimensions:
            sql += "\nGROUP BY " + ", ".join(d["dimension_name"] for d in ddefs)
        if order_by_time:
            time_dims = [d["dimension_name"] for d in ddefs if d.get("category") == "time"]
            if time_dims:
                sql += "\nORDER BY " + ", ".join(time_dims)
        return sql

    # ── filters (structured, never raw SQL fragments) ─────────────────────────────
    def _render_filters(self, filters, dimensions) -> str:
        if not filters:
            return ""
        preds = []
        for f in filters:
            f = f if isinstance(f, Filter) else Filter(**f)
            d = self.get_dimension(f.dimension)        # G5: filter dim must be governed
            col = d["sql_definition"]
            op = f.op.upper()
            if op not in _VALID_OPS:
                raise SemanticError(f"unsupported filter op '{f.op}'")
            if op == "BETWEEN":
                lo, hi = f.value
                preds.append(f"{col} BETWEEN {_lit(lo)} AND {_lit(hi)}")
            elif op in ("IN", "NOT IN"):
                vals = ", ".join(_lit(v) for v in f.value)
                preds.append(f"{col} {op} ({vals})")
            else:
                preds.append(f"{col} {op} {_lit(f.value)}")
        return " AND ".join(preds)


def _lit(v) -> str:
    """Render a Python value as a safe SQL literal (values are structured inputs, never
    raw SQL). Strings are single-quoted with quotes escaped; bools/numbers pass through;
    ISO date strings are emitted as DATE literals."""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if len(s) == 10 and s[4] == "-" and s[7] == "-":   # 'YYYY-MM-DD' -> DATE literal
        return f"DATE '{s}'"
    return "'" + s.replace("'", "''") + "'"
