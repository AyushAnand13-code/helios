"""render_brief_md — turn a Diagnosis + Critic verdict into a Markdown Decision Brief.

Deterministic and offline: every number is a field already computed by the governed
engine / Critic; this module only formats them. Shared by the scheduled autonomous run
(helios.run) and any other surface that needs the executive brief as text.
"""
from __future__ import annotations

from helios.experiment import design_experiment


def _pct(x: float, dp: int = 2) -> str:
    return f"{x * 100:.{dp}f}%"


def _pts(x: float, dp: int = 3) -> str:
    return f"{x * 100:+.{dp}f} pts"


def _money(x: float) -> str:
    return f"${x:,.0f}"


def _experiment_section(d, report) -> list[str]:
    """A powered, sized A/B test for a genuine rate finding (principle #4). Only for
    rate-dominant findings the Critic didn't refute; mix/seasonal/refuted findings are
    acquisition/data issues, not funnel experiments."""
    if report.verdict == "REFUTE" or d.dominant != "rate" or not d.drivers:
        return []
    # Size on the regressed POPULATION, not a single thin cell: pool the driver cells that
    # share the top driver's device (labels are 'channel / device'), so the test runs on
    # realistic traffic. Baseline is the traffic-weighted compare-week conversion.
    top = d.drivers[0]
    device = top["segment"].split(" / ")[-1]
    pool = [c for c in d.drivers if c["segment"].split(" / ")[-1] == device
            and c.get("sessions_t1", 0) > 0]
    elig = sum(c["sessions_t1"] for c in pool)
    if elig <= 0:
        return []
    baseline = sum((c["conv_t1_pct"] / 100.0) * c["sessions_t1"] for c in pool) / elig
    label = device if len(pool) > 1 else top["segment"]
    try:
        # +10% relative is a realistic target for recovering a funnel regression.
        exp = design_experiment(primary_metric="session_conversion_rate", segment=label,
                                baseline_rate=baseline, daily_eligible_sessions=elig / 7.0,
                                mde_rel=0.10)
    except (ValueError, ZeroDivisionError):
        return []
    runtime = (f"~{exp.runtime_days} days (~{exp.runtime_weeks} wks)"
               if exp.runtime_days is not None else "n/a (insufficient traffic)")
    feas = "feasible" if exp.feasible else "SLOW — widen the segment or raise the MDE"
    return [
        "",
        "## Recommended experiment (powered)",
        f"- **Hypothesis:** {exp.hypothesis}",
        f"- **Primary metric:** `{exp.primary_metric}` · **guardrails:** "
        + ", ".join(f"`{g}`" for g in exp.guardrails),
        f"- **Design:** {exp.arms}-arm {exp.split} split · detect +{exp.mde_rel*100:.0f}% "
        f"at alpha={exp.alpha}, power={exp.power:.0%}",
        f"- **Sample size:** {exp.n_per_arm:,}/arm ({exp.total_n:,} total) · "
        f"~{exp.daily_eligible_sessions:,.0f} eligible sessions/day",
        f"- **Runtime:** {runtime} — {feas}",
    ]


def _action(d, report) -> str:
    """The single recommended next step, consistent with the Critic verdict."""
    if report.verdict == "REFUTE":
        why = report.failures[0].detail if report.failures else "a failed integrity check"
        return (f"**Do not act on this as a growth problem.** {why} "
                f"Fix the data / wait for a clean window, then re-run.")
    if not d.significant:
        return ("**Monitor, don't act yet.** The move is not statistically significant — "
                "wait for it to persist before investing.")
    if d.dominant == "mix":
        top = d.drivers[0]["segment"] if d.drivers else "the shifted segment"
        return (f"**Investigate the traffic mix, not the funnel.** The move is composition-"
                f"driven (driver: {top}); look at acquisition/channel changes. Do NOT "
                f"'fix the checkout' — per-segment rates may be unchanged.")
    top = d.drivers[0]["segment"] if d.drivers else "the top segment"
    return (f"**Drill the rate change in `{top}`.** It carries the largest in-segment "
            f"behaviour move — run a funnel-step diagnosis and size a targeted experiment "
            f"there (guardrails: aov, cart_abandonment_rate, net_revenue).")


def render_brief_md(d, report, *, as_of: str, source_label: str,
                    move_label: str = "largest week-over-week session-conversion move") -> str:
    """Render the executive Decision Brief as Markdown.

    d       : helios.diagnosis.Diagnosis
    report  : helios.critic.CritiqueReport
    as_of   : date string for the brief header (e.g. '2026-06-16')
    source_label : where the data came from (e.g. 'BigQuery helios_dev' / 'synthetic')
    """
    direction = "drop" if d.delta < 0 else "rise"
    sig = ("statistically significant" if d.significant
           else "not statistically significant") + f" (p={d.p_value:.3g})"
    risk_word = "at risk" if d.revenue_at_risk < 0 else "upside"

    lines = [
        f"# Helios Decision Brief — {as_of}",
        f"_Autonomous run · source: {source_label} · {move_label}: "
        f"week {d.w0} → {d.w1}_",
        "",
        "## Headline",
        f"Session conversion **{direction}**: {_pct(d.conv_t0)} → {_pct(d.conv_t1)} "
        f"({_pts(d.delta, 2)}), {sig}.",
        f"**Critic verdict: {report.verdict}.**",
        "",
        "## Why it moved (mix vs rate)",
        f"- **mix** {_pts(d.mix)} — traffic composition changed",
        f"- **rate** {_pts(d.rate)} — in-segment behaviour changed",
        f"- **interaction** {_pts(d.interaction)} — both moved together",
        "",
        f"**Dominant effect: {d.dominant.upper()}.** " + (
            "Composition artifact — the funnel itself may be fine."
            if d.dominant == "mix" else
            "Real in-segment behaviour change — worth a funnel/UX investigation."
            if d.dominant == "rate" else
            "Mix and rate moved together — report the interaction separately."),
        "",
        "## Top driver segments",
        "| segment | total | mix | rate | conversion before → after |",
        "|---|---:|---:|---:|---|",
    ]
    for c in d.drivers[:3]:
        lines.append(
            f"| {c['segment']} | {c['total_pts']:+.3f} | {c['mix_pts']:+.3f} | "
            f"{c['rate_pts']:+.3f} | {c['conv_t0_pct']:.2f}% → {c['conv_t1_pct']:.2f}% |")

    lines += [
        "",
        "## Dollar impact",
        f"AOV {_money(d.aov)} · sessions {d.sessions_t1:,}. "
        f"Revenue {risk_word} from the rate change: **{_money(d.revenue_at_risk)}**.",
        "",
        "## Recommended action",
        _action(d, report),
    ]
    lines += _experiment_section(d, report)
    lines += [
        "",
        "## Critic review (verify-then-trust)",
        f"Verdict: **{report.verdict}**",
    ]
    for c in report.checks:
        lines.append(f"- {c.icon} **{c.name}** — {c.detail}")

    lines += [
        "",
        "---",
        "_All figures are governed-mart + deterministic-stats outputs (no hand SQL, no "
        "in-prose math). Attacked by the Critic before shipping._",
        "",
    ]
    return "\n".join(lines)
