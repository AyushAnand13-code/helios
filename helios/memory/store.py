"""MemoryStore — a durable record of prior diagnoses (report-mcp save/recall).

A finding is fingerprinted by `finding_key` (dominant effect + top driver segment +
direction) so the autonomous run can tell "the same finding as last time" from "something
new". Backed by a JSONL file by default (append-only, deterministic, offline); a BigQuery
(`helios_memory`) backend can replace it later behind the same interface.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path("memory") / "diagnoses.jsonl"


def finding_key(dominant: str, segment: str, delta: float) -> str:
    """Stable identity of a finding: same effect + same top segment + same direction."""
    direction = "down" if delta < 0 else "up"
    return f"{dominant}|{segment}|{direction}"


@dataclass
class DiagnosisRecord:
    as_of: str            # date the finding was reported (YYYY-MM-DD)
    w0: str
    w1: str
    key: str
    dominant: str
    segment: str
    direction: str
    delta: float
    revenue_at_risk: float
    verdict: str

    @classmethod
    def from_diagnosis(cls, d, *, as_of: str, verdict: str) -> "DiagnosisRecord":
        seg = d.drivers[0]["segment"] if d.drivers else "(none)"
        return cls(as_of=as_of, w0=d.w0, w1=d.w1,
                   key=finding_key(d.dominant, seg, d.delta),
                   dominant=d.dominant, segment=seg,
                   direction="down" if d.delta < 0 else "up",
                   delta=d.delta, revenue_at_risk=d.revenue_at_risk, verdict=verdict)


class MemoryStore:
    def __init__(self, path: str | Path = DEFAULT_PATH):
        self.path = Path(path)

    def all(self) -> list[DiagnosisRecord]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(DiagnosisRecord(**json.loads(line)))
        return out

    def save_diagnosis(self, record: DiagnosisRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record)) + "\n")

    def recall_prior(self, key: str, *, as_of: str | None = None,
                     within_days: int | None = None) -> list[DiagnosisRecord]:
        """Prior records with this finding key, most recent first. If `as_of`+`within_days`
        are given, only records within that many days before `as_of`."""
        recs = [r for r in self.all() if r.key == key]
        if as_of is not None and within_days is not None:
            ref = date.fromisoformat(as_of)
            recs = [r for r in recs
                    if 0 <= (ref - date.fromisoformat(r.as_of)).days <= within_days]
        return sorted(recs, key=lambda r: r.as_of, reverse=True)
