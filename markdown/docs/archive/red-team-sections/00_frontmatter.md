# Helios — Red-Team Review (Adversarial Stress Test)

**`RED_TEAM_REVIEW.md`** · Version v1.0 · 2026-06-03 · *Mandate: destroy Helios. No redesign. Stress-test the existing architecture.*

**Method.** Four principal critics — Architect, Analytics Engineer, Product Analyst, AI Engineer — independently attacked the live artifacts (Bible, DATA_MODEL, DBT_GUIDE, `semantic_layer.yaml`, MCP/AGENT architecture, `scenarios.yaml`, DEVELOPMENT_PLAN). Findings are brutal but **grounded and cited**. Each is tagged **Fundamental** (cannot be fixed without abandoning the premise) or **Fixable** (sloppiness). This front matter synthesizes; §1–§4 are the full reviews.

**Severity tally:** 12 Critical · 19 High · 14 Medium (45 total). **Fundamental ≈ 25 / Fixable ≈ 20.** The fixable ones are the *least* of Helios's problems.

---

## The Kill-List (ranked, deduplicated across critics)

1. **CRITICAL — Nothing is built; every quantitative claim is an unearned target.** "≥85% accuracy," "<5 min/run," "0 hallucinated columns," "production-grade," the §20.9 results table (0.882, 0.441…) — all are *design intent printed as results*. The only thing "validated" is a YAML referential-integrity **lint**. *(Architect + AI Eng headlines; all 4.)*
2. **CRITICAL — The headline benchmark is circular.** Bible §20.2 admits the labels are "computed analytically by the same decomposition algebra Helios is graded on." On injected aggregates the mix/rate/interaction split is exact **by construction** → the 85% measures whether the system can run its own equation twice. It is a unit test of arithmetic, not diagnostic accuracy. *(AI Eng C; Product Analyst H; Analytics Eng C.)*
3. **CRITICAL — "Diagnose WHY" is an overclaim; the engine computes WHERE.** Mix-vs-rate is *arithmetic attribution* (which segment, mix or rate), not *causal inference* (deploy, price, broken SDK, competitor, holiday — all outside the dimensional space). Proof in its own data: scenario **S021** injects only a `0.62` rate multiplier yet labels it an "iOS WebView payment-SDK regression" — a cause found **nowhere in the dataset**. The causal layer is asserted, never derived. *(Product Analyst C; AI Eng C; Analytics Eng C.)*
4. **CRITICAL — The static, frozen, 3-month dataset is incompatible with the entire autonomous premise.** "Always-on," "scheduled cron," "anomaly detection over time," "source freshness," "day_30 retention," "forecasting," "revenue-at-risk" — every run sees the *same frozen export*. The product's core value (continuous autonomous diagnosis) is **undemonstrable on the data it is built on**. *(Product Analyst C; Architect H; Analytics Eng H.)*
5. **CRITICAL — "Trust" rests on verification that isn't verification.** The Critic and the faithfulness check are *stochastic LLMs with no oracle* grading other stochastic LLMs; "adversarial verification" is sampling, not proof. Meanwhile "0 hallucinated columns" guards the *cheap* failure (a bad column name) and does nothing about the *expensive* one (a confident wrong causal story over correct numbers). The "correct and trusted" thesis is the weakest part. *(AI Eng C; Architect M×2.)*
6. **CRITICAL — The agentic apparatus is grossly disproportionate to the problem.** 5 MCP servers + 7 agents (3 Opus) + an FSM + a hypothesis tree + memory + a vector store… to deliver a `GROUP BY` + a subtraction that `decompose_change` does in ~14 lines over a daily fact with **three usable dimensions**. *(Architect C; AI Eng M; Analytics Eng M; Product Analyst H.)*
7. **CRITICAL — The decomposition mart cannot represent the segments the eval grades against** (and the documented `fct_funnel` lacks the dimensions the semantic layer/hypothesis-tree drill). The "wide-fact" assumption contradicts the documented columns. *(Analytics Eng C; Architect C.)*
8. **HIGH — "Deterministic FSM with model-driven nodes" is a contradiction** that launders stochastic choices (which slice to drill, which story to tell) as determinism. Determinism covers only the SQL/stats, never the answer. *(Architect C; AI Eng H.)*
9. **HIGH — `revenue-at-risk` is a false-persistence counterfactual sold as a hard dollar figure** — it assumes the degraded rate would otherwise have held at its t0/forecast value, which is routinely false. *(Product Analyst C.)*
10. **HIGH — Injected anomalies don't resemble real ones; seasonality/data-quality buckets leak answers through pre-seeded memory.** The benchmark only contains anomalies the algebra can already see, and the Critic "refutes" seasonality using a calendar that was seeded with the answer. *(AI Eng C+H.)*
11. **HIGH — The insight-to-action gap is misdiagnosed; the ROI story is unfounded.** The bottleneck is usually deciding/prioritizing/shipping — which Helios does not do — not the speed of RCA; "days to minutes" assumes RCA *volume* is the cost driver. *(Product Analyst H×2.)*
12. **HIGH — Build-vs-buy and cost/latency are unanswered.** GA4/Amplitude/Mixpanel/Looker already ship anomaly detection + segmentation; the "governed + adversarial-eval" moat is thin and copyable. And 7 agents + tree + Critic re-query loop credibly fitting <5 min / ≤5 GiB is **asserted, never measured**. *(Architect H×2; Product Analyst M; AI Eng H.)*

---

## Cross-cutting themes (where multiple critics converged — the real fatal patterns)

- **Self-referential proof.** Items 1, 2, 5, 10 are one disease: Helios grades and "verifies" itself with its own machinery (its algebra defines the labels; LLMs check LLMs; seeded memory answers the seasonality bucket; the results table is fabricated). There is **no independent oracle anywhere in the trust story.**
- **WHERE masquerading as WHY.** Items 3, 9 + the AE's "arithmetic attribution" finding: the product's defining verb ("diagnose why") describes something the engine cannot do; it relabels arithmetic movement as causation, and even its benchmark labels smuggle in causes the data lacks.
- **A live-product narrative on dead data.** Item 4 + freshness/retention/forecasting/experiment findings: autonomy, scheduling, monitoring, retention, and "designs experiments" are all theater on a frozen 3-month obfuscated export with no live funnel and no one to action a brief.
- **Complexity committed, value hypothetical.** Items 1, 6, 8 + MCP/memory/maintenance findings: maximal architecture (and a multi-tenant/warehouse-agnostic roadmap) sits atop *zero running code*, with a one-person maintenance surface that the "single source of truth" already can't keep consistent (registry filename, schema keys, scenario count, wide-fact dims all drift across docs).

---

## Fundamental vs Fixable

**Fundamental (gut the thesis — cannot be fixed without changing what Helios *is*):** the circular benchmark; WHERE-not-WHY; autonomy-on-frozen-data; verification-by-LLM; apparatus-vs-problem disproportion; deterministic-FSM contradiction; revenue-at-risk counterfactual; build-vs-buy moat; the data simply cannot support day_30 retention / live anomalies / causal claims.

**Fixable (embarrassing, not fatal):** the registry filename + schema-key + scenario-count + wide-fact drifts; the broken cohort SQL + duplicated retention numerators; `MAX`/`ANY_VALUE` corrupting slice keys; the 47-metric bloat (CAC-proxy with no cost data); the strawman 45% baseline; MCP/vector-store over-abstraction.

## Verdict

As an **engineering portfolio artifact**, the *depth* is real. As the **product it claims to be**, the three most-marketed claims — *autonomous diagnosis of WHY*, *proven to 85%*, *correct and trusted* — are each **fundamentally unsupported**: the first by the dataset, the second by circular self-grading, the third by stochastic self-verification, and **all three by the fact that none of it has ever run.** The complexity is fully paid for; the value is entirely promissory.
