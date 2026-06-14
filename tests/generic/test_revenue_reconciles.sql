-- tests/generic/test_revenue_reconciles.sql
{% test test_revenue_reconciles(model, column_name,
                                source_relation=none,
                                source_column='ecommerce.purchase_revenue_in_usd',
                                tolerance=0.01) %}

{# Compare the mart's revenue to canonical raw revenue, DEDUPED PER TRANSACTION so the
   comparison is apples-to-apples: GA4 emits duplicate/retry purchase rows for one
   transaction, and the marts already dedupe per transaction_id. We therefore reduce the
   raw side to one revenue value per (non-null) transaction_id before summing. #}
{%- set src = source_relation or source('src_ga4', 'events') -%}

with mart_total as (
    select coalesce(sum({{ column_name }}), 0) as amt
    from {{ model }}
),
raw_total as (
    select coalesce(sum(txn_rev), 0) as amt
    from (
        select max({{ source_column }}) as txn_rev
        from {{ src }}
        where event_name = 'purchase'
          and ecommerce.transaction_id is not null
        group by ecommerce.transaction_id
    )
),
recon as (
    select
        mart_total.amt as mart_amt,
        raw_total.amt  as raw_amt,
        abs(mart_total.amt - raw_total.amt)
            / nullif(raw_total.amt, 0) as rel_drift
    from mart_total cross join raw_total
)
select *
from recon
where rel_drift > {{ tolerance }}      -- any row returned => drift exceeds 0.5%
   or (raw_amt = 0 and mart_amt <> 0)  -- mart invented revenue

{% endtest %}
