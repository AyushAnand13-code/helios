## Appendix A — Global Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `dbt debug` fails to connect | wrong project/dataset/location or no ADC | set `location: US` (the GA4 sample is US), run `gcloud auth application-default login`, check `profiles.yml` project. |
| "Dataset not found: ga4_obfuscated_sample_ecommerce" | location mismatch | the public dataset is in **US**; your target dataset + job location must be US. |
| Query scans 100s of GB / huge bill | no shard pruning / `SELECT *` | always filter `_TABLE_SUFFIX BETWEEN ...`; set `maximum_bytes_billed`; never `SELECT *` over `events_*`. |
| Step rate > 1 (e.g. `view_to_cart_rate` = 1.4) | occurrence-based flags, not monotonic | use `reached_*` **max-downstream** flags (M3); rerun the monotonicity test. |
| `dim_channels` test fails | an 11th channel group crept in | keep **exactly 10** groups; channel logic only in `channel_group_case()`. |
| Revenue / AOV ~2× too high | `transaction_id` not deduped | dedup orders by `transaction_id` in `fct_orders` (M4). |
| `revenue` ≠ `gross_revenue` totals | session-attributed vs order-grain | they reconcile only at the **grand total**; don't compare per-slice. |
| `validate_semantic.py` fails (dangling ref) | a metric's numerator/denominator/expr names a metric not in the registry | fix the reference or add the metric; the registry is the single source of truth. |
| `semantic-mcp` can't find the registry | filename drift | `mcp_servers.yaml` must point at `models/semantic/semantic_layer.yaml`. |
| `run_query` raises `NotDryRunFirst` | called without a prior `dry_run` | always `dry_run` first (this is the guardrail working — don't bypass it). |
| `decompose_change` golden test off | wrong mix/rate/interaction algebra | mix=`Σ Δwᵢ·rᵢ(t0)`, rate=`Σ wᵢ(t0)·Δrᵢ`, interaction=`Σ Δwᵢ·Δrᵢ`; seed `rng_seed=1729`. |
| Eval accuracy looks great but agents hallucinate | grading on live data, no hallucination gate | grade against the **injected labels**; make hallucination a **hard-zero** CI gate. |
| Critic flags everything seasonal as real | `seasonality_calendar` not seeded | seed Black Friday 2020 / Dec peak / Jan trough (M8). |
| Run never finishes / huge token cost | row-level dumps into LLM context | summarize query results to aggregates before they enter the model; enforce per-agent tool allow-lists. |
| LLM output not byte-reproducible | expecting determinism from the model | the agent layer is graded **statistically** by the eval harness, not asserted byte-identical; only stats/SQL are deterministic. |

## Appendix B — Definition of Done (per level)

- **L1 (after M7):** governed marts + semantic layer + the minimal loop; `reconcile('revenue','day')` matches a hand-written control query to the cent; **0 hallucinated columns**; one anomaly → a Decision Brief in **<5 min**.
- **L2 (after M10):** all 7 agents + 5 MCP servers + the Critic + the eval harness in CI; every finding carries significance + dollar impact + an experiment; **root-cause ≥85% vs ≤45% baseline**; cost under the byte budget.
- **L3 (after M11):** autonomous scheduled runs with memory-driven learning; forecasting / cohorts / RFM; full Critic refutation battery; accuracy holds across all canonical dimensions.

## Appendix C — Minimum-viable Helios (if you have limited time)

You do not have to build all of M0–M12 to have something valuable:

- **A weekend (M0–M5):** the governed dbt marts + the validated semantic layer. This alone is a strong analytics-engineering portfolio piece — correct, tested, documented metrics on real GA4 data, queryable by anyone. **No LLM required.**
- **A week (+ M6, M6b, M7):** add the MCP servers and the minimal loop → governed SQL + deterministic stats + a single automated Decision Brief. This is the "grounded AI analyst" story end-to-end on one path.
- **Two–three weeks (+ M8–M10):** the full 7-agent loop and the benchmark → the headline **85%-vs-45%** result, which is the project's central, defensible claim. This is the L2 portfolio centerpiece.

Build depth-first along the critical path (`DEPENDENCY_MAP.md` §4), not breadth-first. Finance facts, cohorts, the scheduler, and the drill-down UI can all wait.

## Appendix D — Build checklist

```text
[ ] M0  repo + GCP/IAM + dbt config        (dbt debug green)
[ ] M1  sources + macros + seed            (dbt deps/seed)
[ ] M2  staging                            (staging tests green)
[ ] M3  sessionization + funnel KEYSTONE   (monotonicity + uniqueness golden tests)   ★ test first
[ ] M4  marts                              (reconcile to the cent; channels = 10)
[ ] M5  semantic layer live                (validate_semantic.py → 0 dangling refs)
[ ] M6  semantic-mcp + warehouse-mcp       (round-trip + budget gate)
[ ] M6b stats + experiment + report MCP    (decompose_change golden test)
[ ] M7  minimal loop                       (anomaly → brief <5 min; 0 hallucination)   ✅ L1
[ ] M8  memory                             (save/recall; calendars seeded)
[ ] M9  full 7-agent loop                  (PASS findings: significance + $ + experiment)
[ ] M10 eval + CI                          (≥85% vs ≤45%; hallucination 0)             ✅ L2
[ ] M11 autonomy + depth                   (<5 min/run scheduled; all dims)            ✅ L3
[ ] M12 productionization / frontier       (deferred)
```

## Appendix E — Where the code lives (spec doc index)

`DBT_GUIDE.md` (all dbt code: config, sources, staging, intermediate, marts, tests, freshness, lineage, docs) · `DATA_MODEL.md` (tables, grains, keys, ER) · `models/semantic/semantic_layer.yaml` (the registry) · `MCP_ARCHITECTURE.md` (5 servers + skeletons) · `AGENT_ARCHITECTURE.md` (7 agents + FSM + Critic + RCA) · `eval/scenarios/scenarios.yaml` (50 labeled scenarios) · `METRIC_GOVERNANCE_GUIDE.md` + `METRIC_DEPENDENCY_GRAPH.md` (metric governance) · `DEPENDENCY_MAP.md` + `DEVELOPMENT_PLAN.md` (build order) · `CLAUDE.md` (conventions + grounding rules) · `HELIOS_PROJECT_BIBLE.md` (the full 25-section reference).

> If you build nothing else, build M0–M5 correctly. Everything downstream trusts those marts — and they fail *silently* if the keystones (M3) are wrong, so test them first and reconcile to the cent.
