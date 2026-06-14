-- models/intermediate/int_ga4__funnel_steps.sql
-- Materialized as TABLE: physical commit of the session-grain rows before the marts read
-- them, avoiding the ephemeral-inlining collision and the view read-during-build race.
{{ config(materialized='table') }}

with events as (

    select
        session_key,
        event_name,
        event_date,
        transaction_id,
        purchase_revenue_in_usd
    from {{ ref('stg_ga4__events') }}
    where ga_session_id is not null

),

-- per-event MAX-DOWNSTREAM membership: a 'view_item' event marks reached_view_item;
-- a 'purchase' event marks ALL of reached_view_item..reached_purchase, etc.
flagged as (

    select
        session_key,
        event_date,
        transaction_id,
        purchase_revenue_in_usd,

        event_name in (
            'view_item','add_to_cart','begin_checkout',
            'add_shipping_info','add_payment_info','purchase'
        ) as f_view_item,

        event_name in (
            'add_to_cart','begin_checkout',
            'add_shipping_info','add_payment_info','purchase'
        ) as f_add_to_cart,

        event_name in (
            'begin_checkout','add_shipping_info','add_payment_info','purchase'
        ) as f_begin_checkout,

        event_name in (
            'add_shipping_info','add_payment_info','purchase'
        ) as f_add_shipping_info,

        event_name in (
            'add_payment_info','purchase'
        ) as f_add_payment_info,

        event_name = 'purchase' as f_purchase

    from events

),

session_grain as (

    select
        session_key,
        min(event_date)                                  as session_date,

        logical_or(f_view_item)         as reached_view_item,
        logical_or(f_add_to_cart)       as reached_add_to_cart,
        logical_or(f_begin_checkout)    as reached_begin_checkout,
        logical_or(f_add_shipping_info) as reached_add_shipping_info,
        logical_or(f_add_payment_info)  as reached_add_payment_info,
        logical_or(f_purchase)          as reached_purchase,

        -- DEDUPED session revenue: one purchase amount per transaction, summed
        -- across distinct transactions in the (rare) multi-order session.
        coalesce(sum(distinct_txn_rev), 0)               as session_revenue,
        max(transaction_id)                              as transaction_id

    from (
        select
            session_key,
            event_date,
            transaction_id,
            f_view_item, f_add_to_cart, f_begin_checkout,
            f_add_shipping_info, f_add_payment_info, f_purchase,
            -- collapse duplicate purchase rows: one revenue value per txn
            max(purchase_revenue_in_usd) over (
                partition by session_key, transaction_id
            ) as distinct_txn_rev
        from flagged
    )
    group by session_key

)

select * from session_grain
