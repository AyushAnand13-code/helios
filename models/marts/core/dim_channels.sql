-- models/marts/core/dim_channels.sql
-- One row per channel_group (exactly 10). is_paid / is_organic / channel_group_order.
-- channel_group strings come from the SINGLE SOURCE OF TRUTH macro (channel_group_case()),
-- enumerated here once as the conformed dimension.  (Verbatim §5.11.)
{{ config(materialized='table') }}

with channels as (
    select * from unnest([
        struct('Direct'         as channel_group, false as is_paid, false as is_organic,  1 as channel_group_order),
        struct('Organic Search' as channel_group, false as is_paid, true  as is_organic,  2 as channel_group_order),
        struct('Paid Search'    as channel_group, true  as is_paid, false as is_organic,  3 as channel_group_order),
        struct('Display'        as channel_group, true  as is_paid, false as is_organic,  4 as channel_group_order),
        struct('Paid Social'    as channel_group, true  as is_paid, false as is_organic,  5 as channel_group_order),
        struct('Organic Social' as channel_group, false as is_paid, true  as is_organic,  6 as channel_group_order),
        struct('Email'          as channel_group, false as is_paid, true  as is_organic,  7 as channel_group_order),
        struct('Affiliates'     as channel_group, true  as is_paid, false as is_organic,  8 as channel_group_order),
        struct('Referral'       as channel_group, false as is_paid, true  as is_organic,  9 as channel_group_order),
        struct('Other'          as channel_group, false as is_paid, false as is_organic, 10 as channel_group_order)
    ])
)

select
    to_hex(md5(channel_group))   as channel_key,   -- surrogate PK
    channel_group,
    is_paid,
    is_organic,
    channel_group_order
from channels
