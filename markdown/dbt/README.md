# dbt/

The Helios dbt project (BigQuery): `staging -> intermediate -> marts`.

- Build it: `docs/architecture/DBT_GUIDE.md` + `docs/planning/IMPLEMENTATION_PLAYBOOK.md` (milestones M0-M5).
- Consumes the GA4 export `bigquery-public-data.ga4_obfuscated_sample_ecommerce`.
- Feeds the governed marts that `models/semantic/semantic_layer.yaml` exposes as metrics.

_Empty until M0._
