"""render_brief_md — turn a Diagnosis + Critic verdict into a Markdown Decision Brief.

Deterministic and offline: every number is a field already computed by the governed
engine / Critic; this module only formats them. Shared by the scheduled autonomous run
(helios.run) and any other surface that needs the executive brief as text.
"""
from __future__ import annotations


def _pct(x: float, dp: int = 2) -> str:
    return f"{x * 100:.{dp}f}%"


def _pts(x: float, dp: int = 3) -> str:
    return f"{x * 100:+.{dp}f} pts"


def _money(x: float) -> str:
    return f"${x:,.0f}"


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
