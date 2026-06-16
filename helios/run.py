"""helios.run — the autonomous Decision-Brief run (the product's heartbeat, principle #5).

One headless command does what the dashboard does on a click: load the governed funnel,
find the most important week-over-week conversion move, decompose it (mix vs rate), test
significance, price the dollars, attack it with the Critic, and emit a dated Decision
Brief. Designed to run on a schedule (see .github/workflows/daily-brief.yml) so Helios is
proactive, not waiting to be asked.

Data sources:
  --source synthetic   (default) generate a realistic fct_daily_funnel via helios.synth —
                       runs anywhere, no credentials, good for demos and CI.
  --source bigquery    read the real governed marts via helios.diagnosis.load_weekly
                       (needs ADC + a built dbt spine).

Usage:
    python -m helios.run                                   # synthetic, today, ./briefs
    python -m helios.run --source bigquery --project p --dataset helios_dev_marts
    python -m helios.run --out-dir briefs --date 2021-01-31
Optional sink: set HELIOS_SLACK_WEBHOOK to post the headline to Slack.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from helios.diagnosis import weeks_in, biggest_move, run_diagnosis, load_weekly
from helios.critic import critique
from helios.report import render_brief_md
from helios.memory import MemoryStore, DiagnosisRecord, decide


@dataclass
class RunResult:
    as_of: str
    source_label: str
    diagnosis: object            # helios.diagnosis.Diagnosis (or None if not enough data)
    report: object               # helios.critic.CritiqueReport (or None)
    markdown: str
    path: Path | None
    note: str = ""
    status: str = "NEW"          # NEW | SEASONAL | REFUTED | IMMATERIAL | REPEAT | NO_DATA
    suppress_reason: str = ""

    @property
    def alert(self) -> bool:
        """Whether this run should page the team (only fresh, material findings do)."""
        return self.status == "NEW"


# ── data sources ──────────────────────────────────────────────────────────────────
def _weekly_synthetic(end: date, days: int):
    """Build the weekly (week x channel x device) DataFrame helios.diagnosis expects from
    synthetic daily rows — same shape as load_weekly, no BigQuery."""
    import pandas as pd
    from helios.synth.generator import generate_daily_funnel

    rows = generate_daily_funnel(end, days=days)
    df = pd.DataFrame(rows)
    dt = pd.to_datetime(df["event_date"])
    df["week"] = (dt - pd.to_timedelta(dt.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    cols = ["sessions", "view_item_sessions", "add_to_cart_sessions",
            "begin_checkout_sessions", "add_shipping_info_sessions",
            "add_payment_info_sessions", "purchasing_sessions", "revenue"]
    return df.groupby(["week", "channel_group", "device_category"])[cols].sum().reset_index()


def _weekly_bigquery(project: str | None, dataset: str):
    # google-cloud-bigquery imported lazily so the synthetic path never needs it.
    from google.cloud import bigquery
    client = bigquery.Client(project=project) if project else bigquery.Client()
    return load_weekly(client, project or client.project, dataset)


# ── sinks ─────────────────────────────────────────────────────────────────────────
def _post_slack(webhook: str, text: str) -> str:
    """Best-effort Slack post via stdlib (no requests dep). Never raises."""
    import urllib.request
    try:
        req = urllib.request.Request(
            webhook, data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return f"slack: {r.status}"
    except Exception as e:  # noqa: BLE001
        return f"slack: skipped ({type(e).__name__})"


# ── orchestration ─────────────────────────────────────────────────────────────────
def generate(*, source: str = "synthetic", project: str | None = None,
             dataset: str = "helios_dev_marts", days: int = 90,
             as_of: str | None = None, out_dir: str | Path = "briefs",
             end_date: date | None = None,
             memory: MemoryStore | None = None) -> RunResult:
    """Run the full diagnosis -> critic -> brief pipeline and write a dated Markdown brief.
    If a MemoryStore is given, consult it (+ the seasonality calendar) to decide whether
    the finding is NEW (alert + remember) or should be suppressed (SEASONAL / REFUTED /
    IMMATERIAL / REPEAT). Returns the RunResult (also when there isn't enough data)."""
    as_of = as_of or date.today().isoformat()
    end = end_date or date.today()

    if source == "synthetic":
        df = _weekly_synthetic(end, days)
        source_label = f"synthetic ({days}d ending {end.isoformat()})"
    elif source == "bigquery":
        df = _weekly_bigquery(project, dataset)
        source_label = f"BigQuery {dataset}"
    else:
        raise ValueError(f"unknown source '{source}' (use 'synthetic' or 'bigquery')")

    out_dir = Path(out_dir)
    if len(weeks_in(df)) < 2:
        note = "Not enough data: need at least two weeks to compare. No brief written."
        return RunResult(as_of, source_label, None, None, f"# Helios — {as_of}\n\n{note}\n",
                         None, note, status="NO_DATA", suppress_reason=note)

    w0, w1 = biggest_move(df)
    d = run_diagnosis(df, w0, w1)
    report = critique(d)

    # Memory: is this finding worth paging on, or expected / already seen?
    status, suppress_reason = "NEW", "new material finding"
    if memory is not None:
        dec = decide(d, report, as_of=as_of, store=memory)
        status, suppress_reason = dec.status, dec.reason
        if not dec.suppress:
            memory.save_diagnosis(DiagnosisRecord.from_diagnosis(d, as_of=as_of,
                                                                 verdict=report.verdict))

    md = render_brief_md(d, report, as_of=as_of, source_label=source_label)
    banner = (f"> **Status: {status}** — {suppress_reason}. "
              f"{'Alerting the team.' if status == 'NEW' else 'Not alerting (suppressed).'}\n\n")
    md = md.split("\n", 1)
    md = md[0] + "\n" + banner + (md[1] if len(md) > 1 else "")

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{as_of}_decision_brief.md"
    path.write_text(md, encoding="utf-8")
    return RunResult(as_of, source_label, d, report, md, path,
                     status=status, suppress_reason=suppress_reason)


def _summary_line(r: RunResult) -> str:
    if r.diagnosis is None:
        return f"[{r.as_of}] {r.note}"
    d = r.diagnosis
    return (f"[{r.as_of}] {r.status} (Critic {r.report.verdict}): session conversion "
            f"{d.conv_t0*100:.2f}% -> {d.conv_t1*100:.2f}% ({d.delta*100:+.2f}pt), "
            f"dominant={d.dominant}, revenue_at_risk=${d.revenue_at_risk:,.0f}"
            + ("" if r.alert else f" — suppressed ({r.suppress_reason})"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Helios autonomous Decision-Brief run.")
    ap.add_argument("--source", choices=["synthetic", "bigquery"],
                    default=os.environ.get("HELIOS_SOURCE", "synthetic"))
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_MARTS_DATASET", "helios_dev_marts"))
    ap.add_argument("--days", type=int, default=90, help="synthetic window length")
    ap.add_argument("--out-dir", default="briefs")
    ap.add_argument("--date", default=None, help="brief date label YYYY-MM-DD (default today)")
    ap.add_argument("--memory", default=os.environ.get("HELIOS_MEMORY_PATH",
                    "memory/diagnoses.jsonl"), help="memory store path (suppress repeats/seasonal)")
    ap.add_argument("--no-memory", action="store_true", help="disable memory (stateless run)")
    args = ap.parse_args()

    end = (datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today())
    memory = None if args.no_memory else MemoryStore(args.memory)
    r = generate(source=args.source, project=args.project, dataset=args.dataset,
                 days=args.days, as_of=args.date, out_dir=args.out_dir, end_date=end,
                 memory=memory)

    print(_summary_line(r))
    if r.path:
        print(f"Wrote {r.path}")
    # Only page the team on a fresh, material finding — not on repeats or seasonal swings.
    webhook = os.environ.get("HELIOS_SLACK_WEBHOOK")
    if webhook and r.alert:
        print(_post_slack(webhook, _summary_line(r)))
    elif webhook:
        print(f"slack: skipped (status {r.status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
