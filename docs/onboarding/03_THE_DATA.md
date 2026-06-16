# 3. The data: GA4, BigQuery, and dbt (from zero)

This explains the three data tools the project uses. You haven't used them before — that's
fine, here's what each *is* and what it does in Helios.

## GA4 — where the raw data comes from
**GA4 (Google Analytics 4)** is Google's free tool that websites use to track what visitors
do: which pages they view, whether they add to cart, whether they buy. Every action a visitor
takes is an **event** (e.g. `page_view`, `add_to_cart`, `purchase`).

Google publishes a **free, public sample** of this data for a real store — the **Google
Merchandise Store** (sells Google-branded swag) — covering **Nov 2020 to Jan 2021**. That's
our raw data: ~**4.3 million events**. It's real data from a real store, which is why this
project is more credible than a toy dataset.

> **Interview line:** *"It runs on the public GA4 e-commerce sample — real Google Merchandise
> Store data, about 4.3 million events over three months."*

## BigQuery — where the data lives and where queries run
**BigQuery** is Google's cloud **data warehouse** — basically a giant, fast SQL database in
the cloud. The public GA4 data lives there, and that's where all our queries run. Think of it
as "a SQL database you rent from Google by the query."

How tables are named in BigQuery: **`project.dataset.table`** (three parts).
- **project** (`helios-mvp`) = your Google Cloud account; it's what gets **billed** for queries.
- **dataset** = a folder/namespace inside the project (e.g. `helios_dev_marts`).
- **table** = the actual table (e.g. `fct_funnel`).

So the dashboard reads `helios-mvp.helios_dev_marts.fct_funnel`. (That's exactly what the two
sidebar boxes in the dashboard set — see [05_THE_DASHBOARD.md](05_THE_DASHBOARD.md).)

## dbt — the tool that turns raw events into clean tables
Raw GA4 events are messy: one row per event, deeply nested, hard to use. **dbt** ("data build
tool") is a popular tool that **transforms** raw data into clean, well-defined tables using
SQL — and tests them. You write SQL "models," and dbt builds them in the right order and runs
data-quality checks.

In Helios, dbt builds the data in **layers** (this layering is standard analytics-engineering
practice):

```
RAW GA4 events  (4.3M rows, messy)
      │  dbt
      ▼
STAGING   stg_ga4__events / stg_ga4__event_params   ← lightly cleaned, one row per event
      │
      ▼
INTERMEDIATE  int_ga4__sessionized  → int_ga4__funnel_steps
      │        (group events into "sessions"; mark which funnel steps each session reached)
      ▼
MARTS (the clean, final tables the rest of the app uses):
   • fct_funnel        ← one row per SESSION: did it view? add to cart? buy? + revenue
   • fct_daily_funnel  ← the above rolled up to per-day × channel × device
   • fct_orders        ← one row per order, for revenue
   • dim_channels, dim_date  ← lookup tables (the 10 marketing channels; the calendar)
```

- **`fct_` = "fact" tables** (the events/measurements). **`dim_` = "dimension" tables** (the
  descriptive lookups, like the list of channels). This `fct_`/`dim_` naming is industry
  standard (Kimball dimensional modelling).
- A **session** = one visit (all of a user's events grouped into one browsing session). The
  whole funnel is measured per session.

### What "it builds green" means
When you run `dbt build`, it creates all those tables **and** runs ~50 tests (e.g. "the funnel
must be monotonic — you can't have more people *buy* than *visit*"; "revenue must reconcile to
the source"). On the real data it reports **PASS=62, ERROR=0** — i.e. every model built and
every test passed. That's your proof the data layer actually works on real data.

> **Interview line:** *"I model the raw GA4 events into a clean star schema with dbt — staging,
> sessionization, then fact and dimension marts — with ~50 data tests including funnel
> monotonicity and revenue reconciliation. It builds green on the real dataset."*

## The "semantic layer" — one definition per metric
There's one more file: `semantic/semantic_layer.yaml`, the **semantic layer** (or "metric
registry"). It's a catalog that defines, **once**, what every metric and dimension *means* in
SQL — e.g. `session_conversion_rate = purchasing_sessions / sessions`, computed from
`fct_funnel`. Nothing in the app is allowed to invent its own definition; everything pulls
from this catalog. That's how you guarantee "your number = my number" across the whole system.

> **Interview line:** *"Every metric is defined once in a governed semantic layer — 49 metrics,
> 19 dimensions — so there's a single source of truth and no two parts of the system can
> disagree on what 'conversion rate' means."*

Next: **[04_THE_ARCHITECTURE.md](04_THE_ARCHITECTURE.md)** — how all the pieces fit together.
