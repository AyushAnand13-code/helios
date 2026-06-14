-- models/intermediate/int_ga4__sessionized.sql
-- Materialized as TABLE: consumed by BOTH fct_funnel and fct_orders. Ephemeral caused a
-- CTE-name collision; a freshly-created view caused a read-during-build consistency race
-- that zeroed fct_funnel's join. A physical table commits the 360k session rows BEFORE
-- the marts read them — deterministic and cheap at this grain.
{{ config(materialized='table') }}

with events as (

    select *
    from {{ ref('stg_ga4__events') }}
    where ga_session_id is not null   -- drop session-less events (e.g. first_open)

),

sessionized as (

    select
        session_key,
        user_pseudo_id,
        ga_session_id,

        -- session timing
        min(event_date)                                     as session_date,
        min(event_timestamp)                                as session_start_ts,
        max(event_timestamp)                                as session_end_ts,

        -- landing_page = page_location of the EARLIEST event in the session
        array_agg(page_location ignore nulls
                  order by event_timestamp limit 1)[safe_offset(0)] as landing_page,

        -- SESSION-SCOPED source/medium with traffic_source first-touch FALLBACK.
        -- event_source/event_medium = event_params.* (session scope, preferred).
        -- first_touch_* = traffic_source.* (USER first-touch, fallback only).
        coalesce(
            max(event_source),
            max(first_touch_source)
        )                                                   as session_source,
        coalesce(
            max(event_medium),
            max(first_touch_medium)
        )                                                   as session_medium,
        coalesce(
            max(event_campaign),
            max(first_touch_campaign)
        )                                                   as session_campaign,
        max(gclid)                                          as gclid,

        -- device / geo (stable within a session; max() picks the non-null)
        max(device_category)                                as device_category,
        max(operating_system)                               as operating_system,
        max(browser)                                        as browser,
        max(country)                                        as country,
        max(region)                                         as region,
        max(city)                                           as city,

        -- engagement: canonical rule (>= , not >)
        max(case
              when session_engaged = '1'
                or engagement_time_msec >= 10000 then true
              else false
            end)                                            as engaged_session,

        -- new vs returning: first-ever session for this user
        max(case when ga_session_number = 1 then true else false end) as is_new_user,
        max(ga_session_number)                              as ga_session_number

    from events
    group by session_key, user_pseudo_id, ga_session_id

)

select
    s.*,
    -- channel grouping from the SINGLE SOURCE OF TRUTH macro, on the
    -- RESOLVED session-scoped source/medium (+ gclid awareness)
    {{ channel_group_case('s.session_source', 's.session_medium', 's.gclid') }} as channel_group
from sessionized s
