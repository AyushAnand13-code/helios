-- models/staging/stg_ga4__events.sql
-- Materialized as TABLE (not view): session_key is derived from ga_session_id, which is
-- extracted via a LIMIT-1 subquery in get_event_param(). As a view that derivation is
-- recomputed for every downstream model and BigQuery may pick a different param row each
-- time, so two separately-built keystones got MISMATCHED session_keys and fct_funnel's
-- join collapsed to 0. Freezing staging to a table computes session_key ONCE; every
-- downstream model reads the identical, stable key.
{{ config(materialized='table') }}

with source as (

    select
        -- shard suffix 'YYYYMMDD' -> a real DATE partition key
        parse_date('%Y%m%d', _table_suffix)                 as event_date,
        _table_suffix                                       as table_suffix,

        -- identity & event
        event_name                                          as event_name,
        timestamp_micros(event_timestamp)                   as event_timestamp,
        user_pseudo_id                                      as user_pseudo_id,
        user_id                                             as user_id,           -- null on this cookie-grain sample

        -- session id lives in event_params, not a top-level column
        {{ get_event_param('ga_session_id',     'int') }}   as ga_session_id,
        {{ get_event_param('ga_session_number', 'int') }}   as ga_session_number,
        {{ get_event_param('page_location',     'string') }} as page_location,
        {{ get_event_param('session_engaged',   'string') }} as session_engaged,
        {{ get_event_param('engagement_time_msec','int') }} as engagement_time_msec,

        -- SESSION-SCOPED source/medium/campaign (see traffic_source gotcha in 4.1)
        {{ get_event_param('source',   'string') }}          as event_source,
        {{ get_event_param('medium',   'string') }}          as event_medium,
        {{ get_event_param('campaign', 'string') }}          as event_campaign,
        {{ get_event_param('gclid',    'string') }}          as gclid,

        -- USER first-touch attribution (FALLBACK only)
        traffic_source.source                               as first_touch_source,
        traffic_source.medium                               as first_touch_medium,
        traffic_source.name                                 as first_touch_campaign,

        -- device.* (light struct flattening; no joins)
        device.category                                     as device_category,
        device.operating_system                             as operating_system,
        device.web_info.browser                             as browser,
        device.language                                     as device_language,

        -- geo.*
        geo.country                                         as country,
        geo.region                                          as region,
        geo.city                                            as city,

        -- ecommerce.* (purchase rows; usd only per money convention)
        ecommerce.transaction_id                            as transaction_id,
        ecommerce.purchase_revenue_in_usd                   as purchase_revenue_in_usd,
        ecommerce.refund_value_in_usd                       as refund_value_in_usd,
        ecommerce.shipping_value_in_usd                     as shipping_value_in_usd,
        ecommerce.tax_value_in_usd                          as tax_value_in_usd,
        ecommerce.total_item_quantity                       as total_item_quantity

    from {{ source('src_ga4', 'events') }}

    where 1 = 1
    -- PRODUCTION incremental note: although this view is not itself incremental,
    -- it is the upstream of incremental facts. Downstream incrementals prune the
    -- shard scan with a 3-day lookback; to bound the view's own scan you can add:
    --   {% if target.name == 'prod' %}
    --     and parse_date('%Y%m%d', _table_suffix)
    --           between date '2020-11-01' and date '2021-01-31'   -- sample window
    --   {% endif %}
    -- On a LIVE export, replace the fixed window with a relative bound, e.g.
    --   and _table_suffix >= format_date('%Y%m%d', date_sub(current_date(), interval 3 day))
    -- so a daily run scans ~3 shards. Prune via _TABLE_SUFFIX, never SELECT *.

),

final as (

    select
        {{ sessionize() }}                                  as session_key,
        *
    from source

)

select * from final
