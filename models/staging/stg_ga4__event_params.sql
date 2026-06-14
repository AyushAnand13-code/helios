-- models/staging/stg_ga4__event_params.sql
{{ config(materialized='view') }}

with events as (

    select
        parse_date('%Y%m%d', _table_suffix)        as event_date,
        event_name,
        event_timestamp,
        user_pseudo_id,
        event_params                                -- the raw ARRAY<STRUCT> column
    from {{ source('src_ga4', 'events') }}

),

unnested as (

    select
        e.event_date,
        e.event_name,
        timestamp_micros(e.event_timestamp)         as event_timestamp,
        e.user_pseudo_id,
        ep.key                                      as param_key,
        ep.value.string_value                       as string_value,
        ep.value.int_value                          as int_value,
        ep.value.float_value                        as float_value,
        ep.value.double_value                       as double_value,
        -- a single coalesced text projection for convenience downstream
        coalesce(
            ep.value.string_value,
            cast(ep.value.int_value    as string),
            cast(ep.value.float_value  as string),
            cast(ep.value.double_value as string)
        )                                           as value_string
    from events e,
         unnest(e.event_params) as ep

)

select * from unnested
