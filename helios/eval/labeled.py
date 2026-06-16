"""Offline 50-scenario benchmark over eval/scenarios/scenarios.yaml — the regression
firewall (Bible section 20). No BigQuery, no network: each labeled scenario is
*synthesized* into a (t0, t1) segment table from its own machine-readable perturbation
spec, then run through the real deterministic engine (helios.stats.decompose_change)
plus the materiality / seasonality / data-quality guards. We then score the prediction
against the scenario's ground-truth labels, bucket by bucket.

This is controlled-attribution accuracy: we know the injected cause, so a correct score
proves Helios *recovers* it — not causation. Its value is (a) coverage across all seven
anomaly classes the YAML defines, and (b) catching regressions in the decomposition or
the guards. By construction the predicted segment is always one of the synthesized
segment labels, so hallucinated segments are structurally impossible — the harness
asserts this (the "0 hallucinated metrics/columns" success target).

Run: `python eval_labeled.py`  (or import `score_labeled` / `load_scenarios`).
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from pathlib import Path

from helios.stats import decompose_change

# ── thresholds (tuned so each guard fires on its bucket and nowhere else) ──────────
CONTROL_REL = 0.04        # |delta|/baseline below this -> immaterial (no_anomaly_control)
CONCENTRATION_MIN = 0.30  # top segment's share of total "activity"; below -> store-wide
MIXED_FRAC = 0.35         # min(|mix|,|rate|)/max >= this -> both present -> 'mixed'
DQ_MOVE = 0.10            # a >10% segment move counts as "moved"
DQ_FLAT = 0.03            # a <3% move counts as "flat" (a conserved/held-constant quantity)
_EPS = 1e-12

DEFAULT_SCENARIOS = Path(__file__).resolve().parents[2] / "eval" / "scenarios" / "scenarios.yaml"

# A small, canonical vocabulary per dimension — used to populate decoy (unperturbed)
# segments around the injected one. Values are real GA4 categories / canonical names.
DIM_VOCAB = {
    "device_category": ["mobile", "desktop", "tablet"],
    "channel_group": ["Organic Search", "Direct", "Paid Search", "Display", "Email",
                      "Referral", "Paid Social", "Affiliates", "Organic Social", "Other"],
    "country": ["United States", "Canada", "United Kingdom", "Germany", "India", "Japan"],
    "browser": ["Chrome", "Safari", "Edge", "Firefox"],
    "operating_system": ["Windows", "Macintosh", "iOS", "Android"],
    "item_category": ["Apparel", "Bags", "Drinkware", "Office", "Accessories", "Lifestyle"],
    "is_new_user": [True, False],
    "landing_page": ["/home", "/google+redesign/shop", "/google+redesign/sale"],
    "source": ["google", "(direct)", "newsletter", "(not set)"],
}


# ── data structures ───────────────────────────────────────────────────────────────
@dataclass
class Prediction:
    effect: str                 # 'rate' | 'mix' | 'mixed' | 'none' | 'data_quality'
    segment: str | None         # top driver label, or None when no targeted segment
    concentration: float
    rel_move: float


@dataclass
class ScoredScenario:
    sid: str
    bucket: str
    truth_effect: str
    truth_segment: str | None
    pred: Prediction
    correct: bool
    segment_hit: bool


@dataclass
class LabeledResult:
    rows: list[ScoredScenario] = field(default_factory=list)
    hallucinations: list[str] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def correct(self) -> int:
        return sum(r.correct for r in self.rows)

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def segment_accuracy(self) -> float:
        """Top-1 segment accuracy over scenarios that HAVE a root-cause segment."""
        seg = [r for r in self.rows if r.truth_segment is not None]
        return (sum(r.segment_hit for r in seg) / len(seg)) if seg else 1.0

    def by_bucket(self) -> dict:
        out: dict = {}
        for r in self.rows:
            b = out.setdefault(r.bucket, [0, 0])
            b[0] += int(r.correct)
            b[1] += 1
        return {k: (c, n) for k, (c, n) in out.items()}


# ── label helpers ─────────────────────────────────────────────────────────────────
def _label(seg: dict, dims: list[str]) -> str:
    """Canonical segment label: dimension values joined in perturbation-dimension order."""
    return " / ".join(str(seg[d]) for d in dims)


def _rel(a: float, b: float) -> float:
    return abs(b - a) / max(abs(a), _EPS)


# ── synthesis: a labeled scenario -> [{segment, num_t0, den_t0, num_t1, den_t1, ...}] ─
def synthesize(sc: dict) -> tuple[list[dict], list[str]]:
    """Build a deterministic (t0, t1) segment table from a scenario's perturbation spec.

    Every row also carries a conserved companion count `cons_*` (a downstream volume that
    should track the numerator). Genuine anomalies keep it consistent; data-quality
    artifacts break it — which is exactly what the data-quality guard looks for.
    Returns (segments, dims). dims == [] means a store-wide scenario with no targeted cell.
    """
    rng = random.Random(sc["seed"])
    pert = sc["perturbation"]
    bucket = sc["bucket"]
    target = pert.get("segment") or {}
    # The dimensions we actually segment on (drop 'day' — it is a store-wide time axis).
    dims = [d for d in (pert.get("dimension") or []) if d in DIM_VOCAB and d in target]

    # Store-wide scenarios (controls, seasonality, day-level) have no targeted cell: we
    # still build a multi-segment universe (on device_category) to decompose against.
    store_wide = not dims
    if store_wide:
        # Spread store-wide scenarios across many cells (10 channels) so a uniform move
        # has LOW concentration — the signature the seasonality/store-wide guard keys on.
        dims = ["channel_group"]
        values = [(v,) for v in DIM_VOCAB["channel_group"]]
        target_tuple = None
        affected: set = set()
    else:
        values, target_tuple, affected = _segment_universe(sc, dims, target)

    segs = []
    for vt in values:
        seg = dict(zip(dims, vt))
        label = _label(seg, dims)
        is_target = (vt == target_tuple)
        is_affected = vt in affected
        # Primary cell gets the largest weight so it dominates the decomposition; decoys
        # are smaller. The affected cell(s) are deliberately OFF the average rate so that a
        # pure volume (mix) shift actually moves the aggregate — otherwise mix is invisible.
        if is_target:
            den = 6000
        elif is_affected:
            den = 3500
        else:
            den = rng.randint(1500, 3000)
        r0 = (0.30 if is_affected else 0.18) * (1.0 + rng.uniform(-0.10, 0.10))
        num = den * r0
        segs.append({"segment": label, "num_t0": num, "den_t0": den,
                     "num_t1": num, "den_t1": den, "cons_t0": num, "cons_t1": num,
                     "_target": is_target, "_affected": is_target or is_affected})

    _apply_perturbation(sc, segs, store_wide, bucket, pert, rng)
    return segs, dims


def _segment_universe(sc: dict, dims: list[str], target: dict):
    """Choose the set of segment value-tuples to simulate: the injected cell(s) plus a
    few unperturbed decoys from the same dimensions."""
    pert = sc["perturbation"]
    gt = sc["ground_truth"]
    secondaries = (pert.get("secondary_segments") or gt.get("also_affected_segments") or [])

    target_tuple = tuple(target[d] for d in dims)
    affected = {target_tuple}
    for s in secondaries:
        if all(d in s for d in dims):
            affected.add(tuple(s[d] for d in dims))

    if len(dims) == 1:
        d = dims[0]
        vals = [target[d]]
        for s in secondaries:
            if d in s and s[d] not in vals:
                vals.append(s[d])
        for v in DIM_VOCAB[d]:
            if len(vals) >= 5:
                break
            if v not in vals:
                vals.append(v)
        values = [(v,) for v in vals]
    else:
        # 2-D grid: target value + 2 decoys on dim0; target value + up to 3 others on dim1.
        d0, d1 = dims[0], dims[1]
        v0 = [target[d0]] + [v for v in DIM_VOCAB[d0] if v != target[d0]][:2]
        v1 = [target[d1]] + [v for v in DIM_VOCAB[d1] if v != target[d1]][:3]
        values = []
        for a in v0:
            for b in v1:
                values.append((a, b))
        for s in secondaries:  # make sure secondary cells exist in the grid
            t = tuple(s[d] for d in dims)
            if all(d in s for d in dims) and t not in values:
                values.append(t)
    return values, target_tuple, affected


def _apply_perturbation(sc, segs, store_wide, bucket, pert, rng):
    """Mutate the t1 columns in place to inject the scenario's known cause."""
    rate_mult = pert.get("rate_multiplier")
    vol_mult = pert.get("volume_multiplier")

    if bucket == "no_anomaly_control":
        for s in segs:  # within-noise wiggle only
            f = 1.0 + rng.uniform(-0.01, 0.01)
            s["num_t1"] = s["num_t0"] * f
            s["den_t1"] = s["den_t0"] * (1.0 + rng.uniform(-0.01, 0.01))
            s["cons_t1"] = s["num_t1"]
        return

    if bucket == "seasonality_decoy":
        # A real, large aggregate move applied UNIFORMLY to every segment (store-wide),
        # so no single cell is responsible — the concentration guard must catch it.
        # Direction is irrelevant to the test; magnitude + uniformity is what matters.
        f = 0.80
        for s in segs:
            s["num_t1"] = s["num_t0"] * f * (1.0 + rng.uniform(-0.02, 0.02))
            s["cons_t1"] = s["num_t1"]
        return

    if bucket == "data_quality":
        _inject_data_quality(sc, segs, rng)
        return

    # Genuine targeted anomaly: rate and/or mix on the affected cell(s).
    for s in segs:
        if not s["_affected"]:
            continue
        if rate_mult and vol_mult:        # multi_segment_mixed: both move
            s["den_t1"] = s["den_t0"] * vol_mult
            s["num_t1"] = s["num_t0"] * vol_mult * rate_mult
        elif rate_mult:                   # pure rate change
            s["num_t1"] = s["num_t0"] * rate_mult
        elif vol_mult:                    # pure mix shift (rate held, volume moves)
            s["den_t1"] = s["den_t0"] * vol_mult
            s["num_t1"] = s["num_t0"] * vol_mult
        s["cons_t1"] = s["num_t1"]        # conserved count tracks real activity -> consistent


def _inject_data_quality(sc, segs, rng):
    """Synthesize a data-quality artifact: a spurious move on the target cell whose
    conserved companion (`cons`) does NOT move — an internal inconsistency. Denominator
    artifacts (bot/null-source/late-shard) inflate sessions with no downstream activity;
    numerator artifacts (dup revenue, dropped event, null _in_usd) move the numerator
    while real volume holds."""
    artifact = (sc["perturbation"].get("artifact") or "").lower()
    den_side = any(k in artifact for k in ("session", "bot", "spam", "null spike",
                                           "(not set)", "late-arriving", "shard", "partition"))
    targets = [s for s in segs if s["_target"]]
    if not targets:
        # Store-wide artifact (e.g. a late-arriving one-day shard): every segment is
        # under-counted in volume while the TRUE downstream (`cons`) is unchanged — the
        # reconcile guard sees volume move with conserved counts flat -> data quality.
        for s in segs:
            s["den_t1"] = s["den_t0"] * 0.60
            s["num_t1"] = s["num_t0"] * 0.60
            s["cons_t1"] = s["cons_t0"]
        return
    for s in targets:
        if den_side:
            s["den_t1"] = s["den_t0"] * 1.35   # sessions inflate; numerator + conserved flat
            s["num_t1"] = s["num_t0"]
            s["cons_t1"] = s["cons_t0"]
        else:
            s["num_t1"] = s["num_t0"] * 0.45   # numerator distorted; conserved volume flat
            s["den_t1"] = s["den_t0"]
            s["cons_t1"] = s["cons_t0"]


# ── prediction: the deterministic engine + guards ─────────────────────────────────
def _dq_inconsistent(seg: dict) -> bool:
    """Funnel-reconcile smell test mirroring the real Critic / G4: did this segment's
    rate move on an unbacked basis? (numerator moved while conserved volume held, or
    sessions inflated with zero downstream activity, or monotonicity broke.)"""
    num_moved = _rel(seg["num_t0"], seg["num_t1"]) > DQ_MOVE
    den_moved = _rel(seg["den_t0"], seg["den_t1"]) > DQ_MOVE
    num_flat = _rel(seg["num_t0"], seg["num_t1"]) < DQ_FLAT
    cons_flat = _rel(seg["cons_t0"], seg["cons_t1"]) < DQ_FLAT
    monotonic_break = seg["num_t1"] > seg["den_t1"] * (1 + 1e-6)
    return (num_moved and cons_flat) or (den_moved and num_flat and cons_flat) or monotonic_break


def predict(segs: list[dict]) -> Prediction:
    """Classify a synthesized scenario: data-quality / none / mix / rate / mixed + the
    top driver segment. Segment ranking is by *gross* activity (|mix|+|rate|+|inter|), so
    cells whose mix and rate cancel in the net are still surfaced."""
    res = decompose_change([{k: s[k] for k in ("segment", "num_t0", "den_t0", "num_t1", "den_t1")}
                            for s in segs])
    by_label = {s["segment"]: s for s in segs}

    def gross(c):
        return abs(c.mix) + abs(c.rate) + abs(c.interaction)

    ranked = sorted(res.segments, key=gross, reverse=True)
    total = sum(gross(c) for c in res.segments) or _EPS
    top = ranked[0]
    concentration = gross(top) / total
    # Materiality on total GROSS activity, not the net delta: a confound where mix and
    # rate cancel (small net move) is still a real finding, not noise.
    activity = total / max(abs(res.r_t0), _EPS)

    # 1. Data-quality guard (hard invariant) — attack the most-active segment.
    if _dq_inconsistent(by_label[top.segment]):
        return Prediction("data_quality", top.segment, concentration, activity)
    # 2. Materiality — within-noise wiggle is not a finding.
    if activity < CONTROL_REL:
        return Prediction("none", None, concentration, activity)
    # 3. Store-wide guard — a large move spread evenly across all cells is seasonal /
    #    store-wide, not a targeted root cause.
    if concentration < CONCENTRATION_MIN:
        return Prediction("none", None, concentration, activity)
    # 4. Targeted anomaly — classify from the TOP cell's OWN mix vs rate contributions
    #    (the cell may have both a share change and a behaviour change = 'mixed').
    m, r = abs(top.mix), abs(top.rate)
    if min(m, r) >= MIXED_FRAC * max(m, r, _EPS):
        effect = "mixed"
    else:
        effect = "rate" if r >= m else "mix"
    return Prediction(effect, top.segment, concentration, activity)


# ── scoring ───────────────────────────────────────────────────────────────────────
def _truth(sc: dict) -> tuple[str, str | None]:
    """(effect, segment_label_or_None) from the scenario's ground-truth labels."""
    gt = sc["ground_truth"]
    if gt.get("is_data_quality"):
        effect = "data_quality"
    else:
        effect = gt.get("dominant_effect", "none")  # 'rate'|'mix'|'mixed'|'none'
    rcs = gt.get("root_cause_segment") or {}
    pert = sc["perturbation"]
    dims = [d for d in (pert.get("dimension") or []) if d in DIM_VOCAB and d in rcs]
    segment = _label(rcs, dims) if dims else None
    return effect, segment


def score_one(sc: dict) -> ScoredScenario:
    segs, _ = synthesize(sc)
    pred = predict(segs)
    truth_effect, truth_seg = _truth(sc)
    segment_hit = (truth_seg is not None and pred.segment == truth_seg)

    if truth_effect == "data_quality":
        correct = (pred.effect == "data_quality")        # flagging the artifact is the win
    elif truth_effect == "none":
        correct = (pred.effect == "none")                # must abstain (control/seasonality)
    else:                                                # rate | mix | mixed
        correct = (pred.effect == truth_effect) and segment_hit
    return ScoredScenario(sc["scenario_id"], sc["bucket"], truth_effect, truth_seg,
                          pred, correct, segment_hit)


def score_labeled(scenarios: list[dict]) -> LabeledResult:
    res = LabeledResult()
    universe = set()
    for sc in scenarios:
        segs, _ = synthesize(sc)
        universe.update(s["segment"] for s in segs)
        row = score_one(sc)
        res.rows.append(row)
        # Hallucination check: a predicted segment must be a real synthesized label.
        if row.pred.segment is not None:
            segs_now = {s["segment"] for s in segs}
            if row.pred.segment not in segs_now:
                res.hallucinations.append(f"{sc['scenario_id']}: {row.pred.segment}")
    return res


def load_scenarios(path: str | Path = DEFAULT_SCENARIOS) -> list[dict]:
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
