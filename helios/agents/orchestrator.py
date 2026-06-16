"""orchestrate — the plan-execute-critique loop over the 7 agents.

Drives Monitor → Decompose → Diagnose → Critic (gate) → Prescribe → Narrator → Orchestrator,
with every governed step going through the Toolbox (allow-list enforced + traced). The
Critic is a GATE: a REFUTE verdict holds the finding (it isn't shipped or saved). Produces
the same Decision Brief as the flat pipeline, plus the audit trace and a human-readable plan.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from helios.diagnosis import biggest_move, run_diagnosis
from helios.semantic import SemanticLayer
from helios.report.brief_md import recommended_experiment
from .toolbox import Toolbox, TraceEntry


@dataclass
class OrchestratedResult:
    diagnosis: object
    report: object
    status: str                 # NEW | SEASONAL | REFUTED | IMMATERIAL | REPEAT
    suppress_reason: str
    markdown: str
    trace: list[TraceEntry] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    gate: str = "HELD"          # SHIPPED if the Critic passed AND it's a fresh finding

    def trace_str(self) -> str:
        return " → ".join(f"{t.agent}:{t.tool}" for t in self.trace)


def orchestrate(df, *, as_of: str, source_label: str, layer: SemanticLayer | None = None,
                store=None, warehouse=None, calendar=None) -> OrchestratedResult:
    layer = layer or SemanticLayer()
    tb = Toolbox(layer=layer, store=store, warehouse=warehouse, calendar=calendar, as_of=as_of)
    plan: list[str] = []

    # Monitor — pick the move to investigate.
    w0, w1 = biggest_move(df)
    plan.append(f"Monitor: selected the biggest week-over-week move {w0} → {w1}")

    # Decompose + Diagnose — routed through the Toolbox (enforced + traced).
    d = run_diagnosis(
        df, w0, w1,
        decompose=lambda segs: tb.call("Decompose", "decompose_change", segs),
        significance=lambda *a: tb.call("Diagnose", "significance_test", *a))
    plan.append(f"Decompose: split the move into mix/rate/interaction (dominant={d.dominant})")
    plan.append(f"Diagnose: significance p={d.p_value:.2g}, "
                f"revenue_at_risk=${d.revenue_at_risk:,.0f}")

    # Critic — the gate.
    report = tb.call("Critic", "critique", d)
    plan.append(f"Critic: verdict {report.verdict}")

    # Prescribe — only for genuine rate findings the Critic didn't refute.
    if report.verdict != "REFUTE" and d.dominant == "rate":
        exp = recommended_experiment(d)
        if exp is not None:
            tb.call("Prescribe", "design_experiment",
                    primary_metric=exp.primary_metric, segment=exp.segment,
                    baseline_rate=exp.baseline_rate,
                    daily_eligible_sessions=exp.daily_eligible_sessions, mde_rel=exp.mde_rel)
            plan.append(f"Prescribe: sized a {exp.n_per_arm:,}/arm test "
                        f"(~{exp.runtime_days}d, {'feasible' if exp.feasible else 'slow'})")

    # Narrator — writes the brief (no data/math tools).
    md = tb.call("Narrator", "render_brief", d, report,
                 as_of=as_of, source_label=source_label)
    plan.append("Narrator: wrote the Decision Brief")

    # Orchestrator — ship/suppress decision + persistence.
    status, reason = "NEW", "new material finding"
    if store is not None:
        dec = tb.call("Orchestrator", "check_suppression", d, report)
        status, reason = dec.status, dec.reason
        if not dec.suppress:
            tb.call("Orchestrator", "save_diagnosis", d, report.verdict)
            plan.append("Orchestrator: NEW finding — saved to memory")
        else:
            plan.append(f"Orchestrator: suppressed ({status}) — {reason}")

    gate = "SHIPPED" if (report.verdict != "REFUTE" and status == "NEW") else "HELD"
    plan.append(f"Gate: {gate}")
    return OrchestratedResult(d, report, status, reason, md, tb.trace, plan, gate)
