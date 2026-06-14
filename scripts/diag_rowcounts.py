#!/usr/bin/env python
"""Diagnostic: does PARTITION BY event_date drop fct_funnel's rows?
Run: python scripts/diag_rowcounts.py
"""
from google.cloud import bigquery

PROJECT = "helios-mvp"
DS = "helios_dev"
c = bigquery.Client(project=PROJECT)
cfg = bigquery.QueryJobConfig(maximum_bytes_billed=10_000_000_000)


def run(sql):
    return c.query(sql, job_config=cfg).result()


def scalar(sql):
    return list(run(sql))[0][0]


SELECT_BODY = f"""
with sess as (select * from `{PROJECT}.{DS}.int_ga4__sessionized`),
     steps as (select * from `{PROJECT}.{DS}.int_ga4__funnel_steps`)
select
    s.session_key,
    s.session_date as event_date,
    s.channel_group, s.device_category,
    st.reached_purchase,
    coalesce(st.session_revenue, 0.0) as session_revenue
from sess s
join steps st using (session_key)
"""

print("\n--- fct_funnel CTAS isolation ---")
print(f"  current fct_funnel rows        = {scalar(f'SELECT COUNT(*) FROM `{PROJECT}.{DS}.fct_funnel`'):,}")
print(f"  plain SELECT rows              = {scalar(f'SELECT COUNT(*) FROM ({SELECT_BODY})'):,}")

# Plain CTAS (no partition)
run(f"CREATE OR REPLACE TABLE `{PROJECT}.{DS}._diag_plain` AS ({SELECT_BODY})")
print(f"  plain CTAS rows                = {scalar(f'SELECT COUNT(*) FROM `{PROJECT}.{DS}._diag_plain`'):,}")

# Partitioned CTAS (exactly like fct_funnel)
run(f"""CREATE OR REPLACE TABLE `{PROJECT}.{DS}._diag_part`
PARTITION BY event_date
CLUSTER BY device_category, channel_group
AS ({SELECT_BODY})""")
print(f"  partitioned CTAS rows          = {scalar(f'SELECT COUNT(*) FROM `{PROJECT}.{DS}._diag_part`'):,}")

# What do the event_date values actually look like?
print("\n  event_date sample / type:")
for r in run(f"SELECT event_date, CAST(event_date AS STRING) AS as_str FROM ({SELECT_BODY}) LIMIT 3"):
    print(f"    {r['event_date']!r}  (str={r['as_str']})")
print(f"  min/max event_date = ", end="")
r = list(run(f"SELECT MIN(event_date) AS lo, MAX(event_date) AS hi FROM ({SELECT_BODY})"))[0]
print(f"{r['lo']} .. {r['hi']}")
