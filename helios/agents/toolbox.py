"""Toolbox — the single chokepoint every agent calls governed tools through.

It enforces per-agent allow-lists (an agent calling a tool it isn't permitted to use raises
AllowListError) and records an audit trace of (agent, tool) calls. The tools themselves are
the existing deterministic functions — stats / semantic / warehouse / critic / experiment /
memory — so there is exactly one implementation of each, now access-controlled.
"""
from __future__ import annotations
from dataclasses import dataclass

from helios.stats import decompose_change, two_proportion_ztest
from helios.critic import critique
from helios.experiment import design_experiment, required_sample_size, runtime_days
from helios.warehouse import Warehouse
from helios.report import render_brief_md
from helios.memory import decide, DiagnosisRecord
from .roles import allows


class AllowListError(Exception):
    """Raised when an agent calls a tool outside its allow-list (Bible §18.9)."""


@dataclass
class TraceEntry:
    agent: str
    tool: str


class Toolbox:
    def __init__(self, *, layer=None, store=None, warehouse: Warehouse | None = None,
                 calendar=None, as_of: str | None = None):
        self.layer = layer
        self.store = store
        self.warehouse = warehouse
        self.calendar = calendar
        self.as_of = as_of
        self.trace: list[TraceEntry] = []
        self._tools = self._register()

    def _register(self) -> dict:
        def _check_suppression(d, report):
            return decide(d, report, as_of=self.as_of, store=self.store,
                          calendar=self.calendar)

        def _save_diagnosis(d, verdict):
            rec = DiagnosisRecord.from_diagnosis(d, as_of=self.as_of, verdict=verdict)
            self.store.save_diagnosis(rec)
            return rec

        return {
            "decompose_change": decompose_change,
            "significance_test": two_proportion_ztest,
            "reconcile": Warehouse.reconcile,
            "critique": critique,
            "design_experiment": design_experiment,
            "power_analysis": required_sample_size,
            "runtime_estimate": runtime_days,
            "render_brief": render_brief_md,
            "get_metric": (self.layer.get_metric if self.layer else None),
            "build_query": (self.layer.build_query if self.layer else None),
            "run_query": (self.warehouse.run_query if self.warehouse else None),
            "dry_run": (self.warehouse.dry_run if self.warehouse else None),
            "check_suppression": _check_suppression,
            "recall_prior": (self.store.recall_prior if self.store else None),
            "save_diagnosis": _save_diagnosis,
        }

    def call(self, agent: str, tool: str, *args, **kwargs):
        """Execute `tool` on behalf of `agent`, enforcing the allow-list and tracing it."""
        if not allows(agent, tool):
            raise AllowListError(
                f"agent '{agent}' is not permitted to call '{tool}' (per-agent allow-list)")
        fn = self._tools.get(tool)
        if fn is None:
            raise KeyError(f"tool '{tool}' is not available (missing dependency?)")
        self.trace.append(TraceEntry(agent, tool))
        return fn(*args, **kwargs)

    def trace_str(self) -> str:
        return " → ".join(f"{t.agent}:{t.tool}" for t in self.trace)
