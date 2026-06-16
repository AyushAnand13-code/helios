"""warehouse — the sole BigQuery client (grounding rules G3 + G4).

Every query is dry-run cost-checked before it runs (G3, against a fixed byte budget) and
aggregates are reconciled against canonical totals (G4). Governed SQL comes in from
helios.semantic; this layer only estimates, executes, and reconciles — it never composes
SQL itself.
"""
from .client import Warehouse, BudgetExceeded, BYTE_BUDGET_GIB  # noqa: F401
