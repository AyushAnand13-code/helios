"""Warehouse — dry-run-gated BigQuery execution + reconciliation.

G3: every run_query is preceded by a dry_run; if the estimate exceeds the byte budget the
query is refused (narrow the window/dims, don't retry blindly). G4: reconcile() checks an
aggregate against a canonical total and fails past 0.5% drift.

The google-cloud-bigquery import is lazy (inside methods) so importing this module — and
unit-testing the budget/reconcile logic with an injected fake client — needs no GCP deps.
"""
from __future__ import annotations

_GIB = 1024 ** 3
BYTE_BUDGET_GIB = 5.0          # the fixed per-run byte budget (CLAUDE.md success targets)
RECONCILE_TOLERANCE = 0.005    # 0.5% canonical-total drift (G4)


class BudgetExceeded(Exception):
    """Raised when a query's dry-run estimate exceeds the byte budget (G3)."""


class Warehouse:
    def __init__(self, client=None, *, project: str | None = None,
                 budget_gib: float = BYTE_BUDGET_GIB):
        self._client = client            # a bigquery.Client (or a compatible fake in tests)
        self.project = project
        self.budget_gib = budget_gib

    def _client_or_make(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = (bigquery.Client(project=self.project)
                            if self.project else bigquery.Client())
        return self._client

    # ── G3: cost check before execution ───────────────────────────────────────────
    def dry_run(self, sql: str) -> dict:
        """Estimate bytes scanned without running the query."""
        from google.cloud import bigquery
        job = self._client_or_make().query(
            sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        b = int(job.total_bytes_processed or 0)
        gib = b / _GIB
        return {"bytes": b, "gib": gib, "budget_gib": self.budget_gib,
                "within_budget": gib <= self.budget_gib}

    def run_query(self, sql: str, *, enforce_budget: bool = True) -> list[dict]:
        """Dry-run first (G3), then execute and return rows as dicts. Refuses to run a
        query whose estimate exceeds the budget."""
        est = self.dry_run(sql)
        if enforce_budget and not est["within_budget"]:
            raise BudgetExceeded(
                f"query would scan {est['gib']:.2f} GiB > budget {self.budget_gib} GiB "
                f"(G3). Narrow the window or dimensions; do not retry blindly.")
        rows = self._client_or_make().query(sql).result()
        return [dict(r) for r in rows]

    # ── G4: reconcile an aggregate against a canonical total ──────────────────────
    @staticmethod
    def reconcile(segment_total: float, canonical_total: float, *,
                  tolerance: float = RECONCILE_TOLERANCE, label: str = "metric") -> dict:
        """Compare a segmented sum to its canonical grand total; >tolerance fails (G4)."""
        denom = abs(canonical_total) if canonical_total else 1.0
        drift = abs(segment_total - canonical_total) / denom
        return {"label": label, "segment_total": segment_total,
                "canonical_total": canonical_total, "drift": drift,
                "tolerance": tolerance, "reconciles": drift <= tolerance}
