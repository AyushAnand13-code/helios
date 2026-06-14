# Helios — Data Model

**`DATA_MODEL.md`** · Companion to `HELIOS_PROJECT_BIBLE.md` §8–§11, `DBT_GUIDE.md`, and `models/semantic/semantic_layer.yaml` · **Version:** v1.0 · **Date:** 2026-06-03

**Purpose.** This is the canonical, production-grade data model for Helios — the single reference for *what tables exist, at what grain, with which keys, who owns them, and why each one exists*. Helios transforms raw GA4 e-commerce events into a Kimball-style star schema (conformed dimensions + fact tables) through a layered dbt pipeline (`raw → staging → intermediate → marts → semantic`). The marts defined here are the substrate the semantic layer exposes as metrics and the agents diagnose against — so the grain discipline, primary keys, and foreign keys below are load-bearing for the entire product.

## How to use this document

- Read §1–§3 first for the whole picture (layered model → ER diagram → master catalog), then the per-model deep dives (§4 Event, §5 Session, §6 User, §7 Product, §8 Order).
- Every table is documented with **grain · primary key · foreign keys · owner/steward · why it exists**.
- This model is consistent with `DBT_GUIDE.md` (the build-time spec) and feeds the 5 grains the semantic layer queries: `fct_funnel`, `fct_sessions`, `fct_orders`, `fct_order_items`, `fct_cohorts`.

## Conventions & keys (cheat-sheet)

| Item | Rule |
|---|---|
| Session key | `session_key = TO_HEX(MD5(CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING))))`; a session = `(user_pseudo_id, ga_session_id)` |
| User key | `user_pseudo_id` — **cookie-grain** (`user_id` is ~always NULL → no cross-device stitching) |
| Order key | `transaction_id` (deduped) |
| Funnel flags | `reached_*` are **max-downstream monotonic** → `sessions ≥ reached_view_item ≥ … ≥ reached_purchase` |
| Channels | 10 GA4 default groups via one `channel_group_case()` macro; `traffic_source` is user first-touch (gotcha) |
| Money | `*_in_usd` only; rates as `SUM(num)/SUM(den)` after grouping |
| Grains of record | **session** (`fct_funnel`/`fct_sessions`), **transaction** (`fct_orders`); marts are **wide** (denormalized dims) |

## Table of Contents

1. Overview & Layered Model
2. Entity Relationship Diagram
3. Master Table Catalog
4. Event Model
5. Session Model
6. User Model
7. Product Model
8. Order Model
