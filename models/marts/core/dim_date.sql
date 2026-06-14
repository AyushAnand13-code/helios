-- models/marts/core/dim_date.sql
-- Conformed date spine over the build window (vars ga4_start_date..ga4_end_date).
-- NOTE: DBT_GUIDE.md §5.1 names dim_date but ships no SQL for it; this is a
-- straightforward, convention-following implementation (PK date_key; week/month/
-- quarter/day_of_week/is_weekend per §5.4 "dim_date").
{{ config(materialized='table') }}

with spine as (
    select day as event_date
    from unnest(generate_date_array(
        date('{{ var("ga4_start_date") }}'),
        date('{{ var("ga4_end_date") }}')
    )) as day
)

select
    to_hex(md5(cast(event_date as string)))   as date_key,   -- surrogate PK
    event_date,
    extract(year    from event_date)          as year,
    extract(quarter from event_date)          as quarter,
    extract(month   from event_date)          as month,
    extract(isoweek from event_date)          as week,
    extract(dayofweek from event_date)        as day_of_week,   -- 1=Sun .. 7=Sat
    format_date('%A', event_date)             as day_name,
    extract(dayofweek from event_date) in (1, 7) as is_weekend
from spine
