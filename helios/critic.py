"""The Critic — verify-then-trust (non-negotiable principle #2).

Every Helios finding is attacked here before it ships. The Critic re-derives the
guarantees the diagnosis *claims* and tries to falsify them: does the decomposition
actually reconcile, is the move statistically real, is the mix-vs-rate framing honest,
is the dollar figure bounded, and does the funnel even look like clean data? It never
authors SQL or recomputes the decomposition in prose — it audits the deterministic
outputs already on the `Diagnosis` object.

Verdicts:
    SHIP    — survives every check; safe to put in the Decision Brief.
    REVISE  — at least one WARN; ship only with the caveat attached.
    REFUTE  — at least one check failed hard; the finding is not trustworthy as stated.

Usage:
    from helios.critic import critique
    report = critique(diagnosis)          # diagnosis: helios.diagnosis.Diagnosis
    if report.verdict == "REFUTE": ...
    print(report.render())
"""
from __future__ import annotations
from dataclasses import dataclass, field

# Tolerances (mirror the grounding rules): G4 reconcile drift, materiality floor.
RECONCILE_TOL = 0.005        # 0.5% of |delta| — the canonical reconcile threshold
MATERIALITY_PTS = 0.0005     # < 0.05pt aggregate move is noise, not a finding

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Check:
    name: str
    status: str          # PASS | WARN | FAIL
    detail: str

    @property
    def icon(self) -> str:
        return {PASS: "[ok]", WARN: "[warn]", FAIL: "[refuted]"}[self.status]


@dataclass
class CritiqueReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if any(c.status == FAIL for c in self.checks):
            return "REFUTE"
        if any(c.status == WARN for c in self.checks):
            return "REVISE"
        return "SHIP"

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.status == WARN]

    def render(self) -> str:
        lines = [f"CRITIC VERDICT: {self.verdict}"]
        for c in self.checks:
            lines.append(f"  {c.icon:9} {c.name}: {c.detail}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "checks": [{"name": c.name, "status": c.status, "detail": c.detail}
                       for c in self.checks],
        }


def _additivity(d) -> Check:
    """G4 — the decomposition must reconcile: mix + rate + interaction == delta."""
    recomposed = d.mix + d.rate + d.interaction
    drift = abs(recomposed - d.delta)
    tol = max(RECONCILE_TOL * abs(d.delta), 1e-9)
    if drift <= tol:
        return Check("reconcile", PASS,
                     f"mix+rate+interaction = {recomposed*100:+.3f}pt reconciles to "
                     f"delta {d.delta*100:+.3f}pt (drift {drift*100:.4f}pt).")
    return Check("reconcile", FAIL,
                 f"decomposition does NOT reconcile: components sum to "
                 f"{recomposed*100:+.3f}pt vs delta {d.delta*100:+.3f}pt "
                 f"(drift {drift*100:.4f}pt > {tol*100:.4f}pt). Numbers are untrustworthy.")


def _materiality(d) -> Check:
    if abs(d.delta) < MATERIALITY_PTS:
        return Check("materiality", WARN,
                     f"aggregate move is only {d.delta*100:+.3f}pt — below the "
                     f"{MATERIALITY_PTS*100:.2f}pt materiality floor; likely noise.")
    return Check("materiality", PASS,
                 f"move of {d.delta*100:+.3f}pt clears the materiality floor.")


def _significance(d) -> Check:
    if not d.significant:
        return Check("significance", WARN,
                     f"two-proportion test p={d.p_value:.3g} (not significant at "
                     f"alpha=0.05) — do NOT act yet; monitor for persistence.")
    return Check("significance", PASS,
                 f"move is statistically significant (p={d.p_value:.3g}).")


def _mix_vs_rate(d) -> Check:
    """The signature Helios check: a mix-shift must NOT be sold as a funnel defect."""
    if d.dominant == "mix":
        top = d.drivers[0]["segment"] if d.drivers else "the shifted segment"
        return Check("mix-vs-rate framing", WARN,
                     f"dominant effect is MIX (composition), not in-segment behaviour. "
                     f"Reject any 'fix the checkout' action — the lever is acquisition/"
                     f"traffic mix (driver: {top}). Per-segment rates may be unchanged.")
    if d.dominant == "interaction":
        return Check("mix-vs-rate framing", WARN,
                     "dominant effect is INTERACTION (mix and rate moved together) — "
                     "report it separately; do not fold it into a pure rate story.")
    return Check("mix-vs-rate framing", PASS,
                 "dominant effect is RATE (real in-segment behaviour) — a funnel/UX "
                 "investigation in the top driver segment is justified.")


def _dollar_sanity(d) -> Check:
    """Revenue-at-risk must be bounded by what the week could plausibly produce, and
    its sign must agree with the rate effect it is priced from."""
    ceiling = d.sessions_t1 * d.aov  # an upper bound: every session worth one order
    if d.aov <= 0 or d.sessions_t1 <= 0:
        return Check("dollar sanity", FAIL,
                     f"degenerate inputs (aov={d.aov:.2f}, sessions={d.sessions_t1}); "
                     f"revenue-at-risk cannot be priced.")
    if abs(d.revenue_at_risk) > ceiling:
        return Check("dollar sanity", FAIL,
                     f"revenue-at-risk ${d.revenue_at_risk:,.0f} exceeds the maximum "
                     f"plausible ${ceiling:,.0f} (sessions x aov). Implausible.")
    if d.rate != 0 and (d.revenue_at_risk > 0) != (d.rate > 0):
        return Check("dollar sanity", WARN,
                     "revenue-at-risk sign disagrees with the rate effect it is priced "
                     "from — re-check the direction before quoting a dollar figure.")
    return Check("dollar sanity", PASS,
                 f"revenue-at-risk ${d.revenue_at_risk:,.0f} is within the plausible "
                 f"bound (<= ${ceiling:,.0f}).")


def _data_quality(d) -> Check:
    """Cheap reconcile/monotonicity smell test. The macro funnel must be monotonic
    (each step <= the previous); a break means under/over-counting, not behaviour."""
    if not (0.0 <= d.conv_t0 <= 1.0) or not (0.0 <= d.conv_t1 <= 1.0):
        return Check("data quality", FAIL,
                     f"conversion out of [0,1] ({d.conv_t0:.3f} -> {d.conv_t1:.3f}); "
                     f"the marts are inconsistent — fix data before diagnosing.")
    for label, funnel in (("baseline", d.funnel_t0), ("compare", d.funnel_t1)):
        vals = list(funnel.values())
        for (a_name, a), (b_name, b) in zip(funnel.items(), list(funnel.items())[1:]):
            if b > a:
                return Check("data quality", FAIL,
                             f"funnel non-monotonic in {label} week: {b_name} ({b:,}) > "
                             f"{a_name} ({a:,}). Downstream exceeds upstream — a tracking/"
                             f"counting artifact, not a behaviour change.")
        _ = vals
    return Check("data quality", PASS,
                 "funnel is monotonic in both weeks and rates are in [0,1].")


def critique(d) -> CritiqueReport:
    """Run every adversarial check against a Diagnosis (or any object exposing the same
    attributes) and return a verdict. Order: reconcile first (if the math doesn't add
    up nothing else matters), then materiality, significance, framing, dollars, data."""
    return CritiqueReport(checks=[
        _additivity(d),
        _materiality(d),
        _significance(d),
        _mix_vs_rate(d),
        _dollar_sanity(d),
        _data_quality(d),
    ])
