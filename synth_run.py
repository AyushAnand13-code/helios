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

from helios.synth.generator import generate_daily_funnel

TABLE = "fct_daily_funnel"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.environ.get("HELIOS_PROJECT", "helios-mvp"))
    ap.add_argument("--dataset", default=os.environ.get("HELIOS_LIVE_DATASET", "helios_live"))
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    end = (datetime.strptime(args.end_date, "%Y-%m-%d").date()
           if args.end_date else date.today())
    rows = generate_daily_funnel(end, days=args.days)
    print(f"Generated {len(rows):,} rows for {rows[0]['event_date']} .. {rows[-1]['event_date']}")

    from google.cloud import bigquery
    client = bigquery.Client(project=args.project)
    client.create_dataset(bigquery.Dataset(f"{args.project}.{args.dataset}"), exists_ok=True)

    table_id = f"{args.project}.{args.dataset}.{TABLE}"
    schema = [
        bigquery.SchemaField("daily_funnel_key", "STRING"),
        bigquery.SchemaField("event_date", "DATE"),
        bigquery.SchemaField("channel_group", "STRING"),
        bigquery.SchemaField("device_category", "STRING"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("is_new_user", "BOOL"),
        bigquery.SchemaField("sessions", "INTEGER"),
        bigquery.SchemaField("view_item_sessions", "INTEGER"),
        bigquery.SchemaField("add_to_cart_sessions", "INTEGER"),
        bigquery.SchemaField("begin_checkout_sessions", "INTEGER"),
        bigquery.SchemaField("add_shipping_info_sessions", "INTEGER"),
        bigquery.SchemaField("add_payment_info_sessions", "INTEGER"),
        bigquery.SchemaField("purchasing_sessions", "INTEGER"),
        bigquery.SchemaField("transactions", "INTEGER"),
        bigquery.SchemaField("revenue", "FLOAT"),
    ]
    job = client.load_table_from_json(
        rows, table_id,
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    n = client.get_table(table_id).num_rows
    print(f"Loaded {n:,} rows into {table_id}  (WRITE_TRUNCATE).")
    print(f"Point the dashboard at dataset '{args.dataset}' to see current weeks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
