-- models/marts/finance/fct_orders.sql
-- One deduped row per transaction_id (PK order_key). Wide channel/device/date dims.
-- gross/net/refund/shipping/tax. Small fact -> full table rebuild.
--
-- RECONCILED vs DBT_GUIDE.md §5.10 (its printed SQL won't compile here):
--   * dims pulled from int_ga4__sessionized, NOT ref('fct_sessions') (never defined in the guide)
--   * ga_session_id is in event_params, so session_key is built with get_event_param(...)
--     fed into sessionize(); the per-row sessionize expr is collapsed with any_value over order_key
{{ config(materialized='table') }}

with raw_purch as (
    select
        ecommerce.transaction_id                              as order_key,
        user_pseudo_id,
        {{ get_event_param('ga_session_id', 'int') }}         as ga_session_id,
        timestamp_micros(event_timestamp)                     as order_ts,
        date(timestamp_micros(event_timestamp))               as event_date,
        ecommerce.purchase_revenue_in_usd                     as gross_revenue,
        ecommerce.refund_value_in_usd                         as refund_value_in_usd,
        ecommerce.shipping_value_in_usd                       as shipping_value_in_usd,
        ecommerce.tax_value_in_usd                            as tax_value_in_usd,
        ecommerce.total_item_quantity                         as total_item_quantity,
        ecommerce.unique_items                                as unique_items
    from {{ source('src_ga4','events') }}
    where event_name = 'purchase'
      and ecommerce.transaction_id is not null               -- exclude untagged purchases
      and _table_suffix between
            replace('{{ var("ga4_start_date") }}', '-', '')
        and replace('{{ var("ga4_end_date") }}',   '-', '')  -- shard prune the static sample
),

purch as (
    -- collapse duplicate purchase rows (GA4 emits retries/multi-stream) to one per txn
    select
        order_key,
        any_value(user_pseudo_id)                            as user_pseudo_id,
        any_value({{ sessionize('user_pseudo_id', 'ga_session_id') }}) as session_key,
        any_value(order_ts)                                  as order_ts,
        any_value(event_date)                                as event_date,
        any_value(gross_revenue)                             as gross_revenue,
        any_value(refund_value_in_usd)                       as refund_value_in_usd,
        any_value(shipping_value_in_usd)                     as shipping_value_in_usd,
        any_value(tax_value_in_usd)                          as tax_value_in_usd,
        any_value(total_item_quantity)                       as total_item_quantity,
        any_value(unique_items)                              as unique_items
    from raw_purch
    group by order_key
),

dims as (
    -- pull the wide session dims so fct_orders slices without a runtime join
    select session_key, channel_group, device_category, country
    from {{ ref('int_ga4__sessionized') }}
)

select
    p.order_key,
    p.session_key,
    p.user_pseudo_id,
    p.event_date,
    p.order_ts,
    coalesce(d.channel_group, 'Other')                       as channel_group,  -- wide
    d.device_category,
    d.country,
    p.gross_revenue,
    coalesce(p.refund_value_in_usd, 0.0)                     as refund_value_in_usd,
    p.gross_revenue - coalesce(p.refund_value_in_usd, 0.0)   as net_revenue,
    coalesce(p.shipping_value_in_usd, 0.0)                   as shipping_value_in_usd,
    coalesce(p.tax_value_in_usd, 0.0)                        as tax_value_in_usd,
    p.total_item_quantity,
    p.unique_items
from purch p
left join dims d using (session_key)   -- left join: keep orders even if session dim is missing
