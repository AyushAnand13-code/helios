-- tests/assert_session_conversion_rate_bounds.sql
-- Session->purchase conversion on this GA4 sample sits ~1-4%.  A rate of 0,
-- a rate >100% (impossible), or a wild swing means sessionization or the
-- funnel flags broke.  Bounds are intentionally generous to avoid false
-- alarms on Black Friday / holiday peaks within the window.  (Verbatim §6.3.)
with daily as (
    select
        event_date,
        sum(purchasing_sessions) as purchasers,
        sum(sessions)            as sessions
    from {{ ref('fct_daily_funnel') }}
    group by 1
)
select
    event_date,
    purchasers,
    sessions,
    safe_divide(purchasers, sessions) as conv_rate
from daily
where sessions > 0
  and (
        safe_divide(purchasers, sessions) > 1.0       -- impossible
     or safe_divide(purchasers, sessions) < 0.0005    -- effectively zero -> broken
     or safe_divide(purchasers, sessions) > 0.20      -- implausibly high -> broken
  )
