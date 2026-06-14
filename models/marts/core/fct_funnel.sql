-- models/marts/core/fct_funnel.sql
-- Session grain (PK session_key). Joins int_ga4__sessionized + int_ga4__funnel_steps 1:1.
-- Wide session dims + monotonic reached_* flags + session_revenue. PRIMARY session grain.
--
-- RECONCILED vs DBT_GUIDE.md §5.8 (its printed SQL doesn't match the M3 keystones):
--   * event_date  <- s.session_date              (guide used a non-existent session_start_micros)
--   * source/medium <- s.session_source / s.session_medium  (keystone names them session_*)
--   * is_new_user <- s.is_new_user               (already derived in the keystone)
--   * dropped st.did_session_start               (did_* is RETIRED; not emitted by the keystone)
--   * incremental predicate uses session_date    (a real DATE column)
-- STATIC-SAMPLE / SANDBOX RECONCILIATION: plain `table` (full rebuild via CREATE TABLE AS),
-- NO partition_by / cluster_by. On the BigQuery free tier, a `PARTITION BY event_date` CTAS
-- silently produced a 0-row table (verified: plain CTAS = 360k rows, partitioned = 0) even
-- with valid in-range dates. Partitioning adds nothing on a static 360k-row sample. Restore
-- partition_by + cluster_by (and incremental) for a live export on a billed project.
{{ config(materialized='table') }}

with sess as (
    select * from {{ ref('int_ga4__sessionized') }}
    {% if is_incremental() %}
      where session_date >= date_sub(_dbt_max_partition, interval 3 day)
    {% endif %}
),

steps as (
    select * from {{ ref('int_ga4__funnel_steps') }}
)

select
    -- keys / partition
    s.session_key,
    s.user_pseudo_id,
    s.session_date                                      as event_date,   -- partition col

    -- wide, denormalized session dimensions (no runtime join needed downstream)
    s.channel_group,
    s.session_source                                    as source,
    s.session_medium                                    as medium,
    s.landing_page,
    s.device_category,
    s.operating_system,
    s.browser,
    s.country,
    s.region,
    s.is_new_user,
    s.engaged_session,

    -- monotonic, max-downstream funnel flags
    -- (sessions >= reached_view_item >= ... >= reached_purchase)
    st.reached_view_item,
    st.reached_add_to_cart,
    st.reached_begin_checkout,
    st.reached_add_shipping_info,
    st.reached_add_payment_info,
    st.reached_purchase,

    -- per-session deduped revenue (one purchase_revenue per distinct transaction_id)
    coalesce(st.session_revenue, 0.0)                   as session_revenue
from sess s
join steps st using (session_key)   -- 1:1; both are session-grained on session_key
