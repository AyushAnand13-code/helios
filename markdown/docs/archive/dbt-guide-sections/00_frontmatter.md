# Helios — dbt Engineering Guide

**`DBT_GUIDE.md`** · Companion to `HELIOS_PROJECT_BIBLE.md` §15–§17 (Analytics Engineering, dbt, BigQuery) and §8 (Data Model) · **Version:** v1.0 · **Date:** 2026-06-03

**Purpose.** This is the production-grade analytics-engineering handbook for Helios — the standalone reference for the dbt layer that transforms raw GA4 events into governed marts. Those marts are the foundation of the entire product: the semantic layer (`models/semantic/semantic_layer.yaml`) exposes them as metrics, and the agents compose those metrics via `semantic-mcp` — they never hand-write SQL. Correct, tested, documented, fresh marts are therefore non-negotiable. It is written assuming Helios will eventually run **production-grade and multi-tenant**, while staying honest about the static public sample dataset it is currently built on.

## How to use this guide

- Build in dependency order (`DEPENDENCY_MAP.md` M1–M5): sources → staging → intermediate (the two keystones) → marts → semantic layer.
- This guide is the *how* of the dbt layer; `CLAUDE.md` is the operating rules, the Bible is the *why*, `METRIC_GOVERNANCE_GUIDE.md` owns the metric definitions downstream of these marts.
- Every code block is real and copy-usable. The keystones (sessionization, `reached_*` monotonicity, revenue reconciliation) fail **silently** — write their golden tests first (§6).

## Conventions cheat-sheet

| Area | Rule |
|---|---|
| Layers / prefixes | `stg_<source>__<entity>` → `int_<source>__<entity>` → `fct_*` / `dim_*`; one model per file; no cross- or upward-layer refs; snake_case |
| Materializations | staging = `view`, intermediate = `ephemeral`, marts/core = `incremental` (`insert_overwrite`), finance/growth/dims = `table`, semantic = `view` |
| Partition / cluster | core facts: `partition_by` `event_date` (DATE, day) + `cluster_by` `[device_category, channel_group]`; `require_partition_filter` on large facts |
| Incremental | `insert_overwrite` + 3-day `is_incremental()` lookback (re-materializes recent partitions for late shards) |
| Session key | `session_key = TO_HEX(MD5(CONCAT(user_pseudo_id, '-', CAST(ga_session_id AS STRING))))`; `sessions = COUNT(DISTINCT session_key)` |
| Funnel flags | `reached_*` are **max-downstream monotonic** → `sessions ≥ reached_view_item ≥ … ≥ reached_purchase`; step rates ≤ 1 by construction (`did_*` retired) |
| Engaged session | `session_engaged = '1' OR engagement_time_msec >= 10000` |
| Channel grouping | exactly 10 groups, defined in **one** macro `channel_group_case()`; `traffic_source` is user first-touch, so prefer session-scoped `event_params` source/medium |
| Money / rates | `*_in_usd` columns only; rates as `SUM(num)/SUM(den)` after grouping (Simpson's-paradox defense) |
| Marts shape | **wide** (denormalized with descriptive dims) so the semantic layer slices without runtime joins |

## Table of Contents

1. dbt Project Structure
2. Source Models
3. Staging Models
4. Intermediate Models
5. Marts
6. Testing Strategy
7. Freshness Strategy
8. Lineage Strategy
9. Documentation Strategy
10. Production-Readiness Checklist
