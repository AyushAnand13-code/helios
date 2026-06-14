# Helios Eval Benchmark — Validation Report

**Validated:** 50 scenarios across 7 bucket files (S001–S050).
**Verdict:** PASS (1 advisory note; no blocking violations).

## Summary table

| Bucket | File | Count | ID range | Target metrics used | Issues |
|---|---|---|---|---|---|
| single_segment_rate | 01_single_segment_rate.yaml | 10 | S001–S010 | checkout_to_purchase_rate, view_to_cart_rate, cart_to_checkout_rate, session_conversion_rate, cart_abandonment_rate | none |
| single_segment_mix | 02_single_segment_mix.yaml | 10 | S011–S020 | session_conversion_rate, aov, revenue_per_session, checkout_to_purchase_rate | none |
| multi_segment_rate | 03_multi_segment_rate.yaml | 6 | S021–S026 | checkout_to_purchase_rate, session_conversion_rate, view_to_cart_rate, cart_to_checkout_rate, cart_abandonment_rate | none |
| multi_segment_mixed | 04_multi_segment_mixed.yaml | 6 | S027–S032 | view_to_cart_rate, checkout_to_purchase_rate, cart_to_checkout_rate, session_conversion_rate | none |
| seasonality_decoy | 05_seasonality_decoy.yaml | 6 | S033–S038 | session_conversion_rate, revenue, aov, purchasing_sessions, sessions | none |
| no_anomaly_control | 06_no_anomaly_control.yaml | 6 | S039–S044 | session_conversion_rate, view_to_cart_rate, aov, cart_to_checkout_rate, engagement_rate, revenue_per_session | none |
| data_quality | 07_data_quality.yaml | 6 | S045–S050 | aov, sessions, session_conversion_rate, view_to_cart_rate, revenue_per_session | note (see below) |
| **TOTAL** | | **50** | **S001–S050** | | |

## Checks performed

1. **Count / IDs / seeds** — Total = 50. IDs S001..S050, unique, no gaps. Per-bucket counts 10/10/6/6/6/6/6 match spec. Seeds 1001–1050, all unique (one per scenario, seed N+1000 aligned to scenario index).

2. **Canonical names** — Every `target_metric` and `funnel_step` numerator/denominator is a canonical metric (seasonality/data-quality scenarios using a non-ratio metric like `revenue`, `sessions`, `purchasing_sessions` correctly set numerator/denominator to `null`). Every dimension key is canonical. All `channel_group` values are among the 10 GA4 groups. `device_category` values are all desktop/mobile/tablet. All `operating_system`, `browser`, `country`, `item_category`, `landing_page`, `is_new_user` values are from the allowed lists.

3. **Windows** — All baseline/inject_at/eval_window dates fall within 2020-11-01..2021-01-31. Every `eval_window.start == inject_at` (so start >= inject_at holds). Baseline precedes inject_at in all 50. (S033 has an intentional gap between baseline end 2020-12-25 and inject_at 2021-01-02 — Christmas-peak baseline vs January-trough eval — which is valid: baseline still precedes inject_at.)

4. **Required fields** — All 50 scenarios carry the full required field set (scenario_id, title, bucket, anomaly_type, seed, three windows, target_metric, anomaly, perturbation, ground_truth with all five sub-fields, expected_diagnosis, expected_recommendation, expected_revenue_impact with revenue_at_risk_usd + basis + direction).

5. **Logic / bucket semantics**
   - Rate buckets (01, 03): `rate_multiplier` set, `volume_multiplier: null`, `dominant_effect: rate`, mix & interaction = 0. ✓
   - Mix bucket (02): `volume_multiplier` set, `rate_multiplier: null`, `dominant_effect: mix`, rate & interaction = 0; recommendations are acquisition/traffic-mix actions and explicitly say NOT a funnel experiment. ✓ Favorable-mix gains (S019, S020) correctly set revenue_at_risk_usd 0 / direction none.
   - Mixed bucket (04): both multipliers set, all three of mix/rate/interaction non-zero. ✓
   - Seasonality decoys (05), controls (06), data-quality (07): `anomaly_type: none`, `revenue_at_risk_usd: 0`, `direction: none`. Decoys set `is_seasonality_decoy: true`; data-quality set `is_data_quality: true`; controls set both false. ✓
   - Data-quality recommendations are all pipeline/instrumentation fixes (dedup, backfill, bot-filter, exclude partition) and explicitly say do NOT launch an experiment. ✓
   - Direction variety: degradations dominate; improvements present (S009, S010 rate gains; S019, S020 favorable mix; S025, S029 multi/mixed gains).

## Advisory note (non-blocking)
- **S046, S048** use `source: "(not set)"` as the perturbation/root-cause segment value. `"(not set)"` is not in the foundation's allowed dimension-value lists, but it is the intended, correct artifact value for these data-quality scenarios (NULL-spike / mis-bucketed attribution), where the whole point is that traffic collapses into the `(not set)` source bucket. This is semantically correct for the data_quality bucket and is recorded as a note rather than a violation.
