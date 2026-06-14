-- models/marts/core/fct_daily_funnel.sql
-- Additive daily funnel: COUNT(DISTINCT IF(reached_*, session_key, NULL)) per step + revenue.
-- Grouped by event_date x canonical dims. RATES ARE NOT STORED (semantic layer computes them).
-- Aggregates fct_funnel (carries session_revenue) -- NOT int_ga4__funnel_steps.  (Verbatim §5.9.)
-- STATIC-SAMPLE / SANDBOX RECONCILIATION: plain `table`, NO partition_by (a partitioned
-- CTAS silently yields 0 rows on the free tier — see fct_funnel note). Restore for prod.
{{ config(materialized='table') }}

with funnel as (
    select * from {{ ref('fct_funnel') }}
    {% if is_incremental() %}
      where event_date >= date_sub(_dbt_max_partition, interval 3 day)
    {% endif %}
)

select
    -- surrogate PK over the grain columns
    {{ dbt_utils.generate_surrogate_key(
         ['event_date','channel_group','device_category','country','is_new_user']) }}
                                                                          as daily_funnel_key,
    event_date,
    channel_group,
    device_category,
    country,
    is_new_user,
    -- additive step counts (re-aggregatable across any slice)
    count(distinct session_key)                                          as sessions,
    count(distinct if(reached_view_item,         session_key, null))     as view_item_sessions,
    count(distinct if(reached_add_to_cart,       session_key, null))     as add_to_cart_sessions,
    count(distinct if(reached_begin_checkout,    session_key, null))     as begin_checkout_sessions,
    count(distinct if(reached_add_shipping_info, session_key, null))     as add_shipping_info_sessions,
    count(distinct if(reached_add_payment_info,  session_key, null))     as add_payment_info_sessions,
    count(distinct if(reached_purchase,          session_key, null))     as purchasing_sessions,
    count(distinct if(reached_purchase and session_revenue > 0, session_key, null)) as transactions,
    sum(session_revenue)                                                 as revenue
from funnel
group by event_date, channel_group, device_category, country, is_new_user
-- NOTE: session_conversion_rate etc. are NOT selected here. They are derived in
-- semantic_layer.yaml as SUM(purchasing_sessions)/SUM(sessions) after grouping.
