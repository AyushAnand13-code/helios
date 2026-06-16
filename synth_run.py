#!/usr/bin/env python
"""synth_run.py — write a fresh, recent-dated synthetic fct_daily_funnel to BigQuery.

Generates a rolling 90-day window ending today and loads it into
`<project>.<dataset>.fct_daily_funnel` (default dataset: helios_live), so the dashboard /
brief / eval show CURRENT weeks. Your real dbt pipeline (helios_dev) is untouched.

Usage:
    python synth_run.py
    python synth_run.py --project helios-mvp --dataset helios_live --days 90
"""
from __future__ import annotations
import argparse
import os
import sys
from datetime import date, datetime

from helios.synth.generator import generate_daily_funnel, generate_funnel_sessions

_DAILY_SCHEMA_COLS = [
    ("daily_funnel_key", "STRING"), ("event_date", "DATE"), ("channel_group", "STRING"),
    ("device_category", "STRING"), ("country", "STRING"), ("is_new_user", "BOOL"),
    ("sessions", "INTEGER"), ("view_item_sessions", "INTEGER"),
    ("add_to_cart_sessions", "INTEGER"), ("begin_checkout_sessions", "INTEGER"),
    ("add_shipping_info_sessions", "INTEGER"), ("add_payment_info_sessions", "INTEGER"),
    ("purchasing_sessions", "INTEGER"), ("transactions", "INTEGER"), ("revenue", "FLOAT"),
]
_FUNNEL_SCHEMA_COLS = [
    ("session_key", "STRING"), ("event_date", "DATE"), ("channel_group", "STRING"),
    ("device_category", "STRING"), ("country", "STRING"), ("is_new_user", "BOOL"),
    ("reached_view_item", "BOOL"), ("reached_add_to_cart", "BOOL"),
    ("reached_begin_checkout", "BOOL"), ("reached_add_shipping_info", "BOOL"),
    ("reached_add_payment_info", "BOOL"), ("reached_purchase", "BOOL"),
    ("session_revenue", "FLOAT"),
]


def _load(client, bigquery, table_id, rows, cols):
    schema = [bigquery.SchemaField(n, t) for n, t in cols]
    client.load_table_from_json(
        rows, table_id,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
    ).result()
    print(f"Loaded {client.get_table(table_id).num_rows:,} rows into {table_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_LIVE_DATASET", "helios_live"))
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--scale", type=float, default=0.12,
                    help="session-grain downsample for fct_funnel (rates preserved)")
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    end = (datetime.strptime(args.end_date, "%Y-%m-%d").date()
           if args.end_date else date.today())
    daily = generate_daily_funnel(end, days=args.days)
    sessions = generate_funnel_sessions(end, days=args.days, scale=args.scale)
    print(f"Generated {len(daily):,} daily rows + {len(sessions):,} session rows "
          f"for {daily[0]['event_date']} .. {daily[-1]['event_date']}")

    from google.cloud import bigquery
    client = bigquery.Client(project=args.project)
    client.create_dataset(bigquery.Dataset(f"{args.project}.{args.dataset}"), exists_ok=True)

    # fct_funnel is what the GOVERNED diagnosis reads; fct_daily_funnel is kept for the
    # pre-aggregated/legacy view.
    _load(client, bigquery, f"{args.project}.{args.dataset}.fct_funnel",
          sessions, _FUNNEL_SCHEMA_COLS)
    _load(client, bigquery, f"{args.project}.{args.dataset}.fct_daily_funnel",
          daily, _DAILY_SCHEMA_COLS)
    print(f"Point the dashboard at dataset '{args.dataset}' to see current weeks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
