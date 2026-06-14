-- tests/assert_funnel_monotonicity.sql
-- The reached_* flags are MAX-DOWNSTREAM by construction; any session that
-- violates the chain means the monotonic roll-up logic broke.  Returns the
-- offending sessions (0 rows = pass).  (Verbatim §6.3.)
select
    session_key,
    reached_view_item, reached_add_to_cart, reached_begin_checkout,
    reached_add_shipping_info, reached_add_payment_info, reached_purchase
from {{ ref('fct_funnel') }}
where reached_purchase           > reached_add_payment_info
   or reached_add_payment_info   > reached_add_shipping_info
   or reached_add_shipping_info  > reached_begin_checkout
   or reached_begin_checkout     > reached_add_to_cart
   or reached_add_to_cart        > reached_view_item
