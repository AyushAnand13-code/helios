## Principal Product Analyst Review

**Headline kill.** Helios sells "diagnose *why* the funnel moved" but its engine only computes *where* the arithmetic moved (which segment, mix vs. rate). The actual "why" — a deploy, a price change, a broken SDK, a competitor, a holiday — lives entirely outside the dimensional space Helios can query, yet the product's value prop, its benchmark labels (`expected_diagnosis`), and its sales pitch all assert that causal layer anyway. The system's own scenario file proves this: in S021 the injector does nothing but multiply a rate by 0.62, but the label "expected_diagnosis" claims a "payment SDK regression on iOS WebView" — a fact found nowhere in the data and impossible to derive. Helios is an attribution calculator wearing a diagnosis costume, and the costume is the entire business case.

---

### [CRITICAL] "Diagnose WHY" is an unbridgeable overclaim — the engine produces WHERE

**Claim attacked.** Bible §1.1/§4.1: "continuously diagnoses *why* an e-commerce funnel is moving"; §2.4: dashboards "report *what*, never *why*… Helios provides causal-style attribution." §1.2 names the category "autonomous growth diagnosis" whose promise is "causal-style attribution of metric movement."

**Why it fails.** The technical centerpiece (§2.3 decomposition) answers a strictly *positional* question: which segment's weight or rate moved, and by how much. That is WHERE, not WHY. The causes a Head of Growth actually needs — "you shipped a checkout regression," "Safari broke third-party cookies," "a competitor undercut price," "it's just January" — are not columns in `fct_daily_funnel`; they are exogenous events. Helios literally cannot observe them. The Bible silently smuggles the causal layer in via narrative: the scenario labels (scenarios.yaml S021 "payment SDK regression," S023 "PDP price-display change," S024 "shipping-calculator failure," S026 "forced account-creation gate") are the *injector's* fictional cover story, never something the pipeline could recover from a rate multiplier. Grading the LLM against those strings rewards plausible storytelling, not diagnosis. "Causal-style" is the tell: it is the adjective you use when you cannot say "causal."

**Fundamental.** The data lacks cause columns.

---

### [CRITICAL] The autonomous / always-on value prop is undemonstrable on a frozen 3-month dataset

**Claim attacked.** §1.1: "an always-on AI Growth Analyst… diagnosis becomes a continuous, autonomous, proactive background process. Every scheduled run, Helios re-derives the full… funnel." §1.4 vision: "before a human has to ask." §4.4 anti-product: "runs on a schedule and reports without being asked."

**Why it fails.** The entire wedge is *autonomy over a live funnel*, and there is no live funnel. The dataset is static, historical, obfuscated, ~2020-11-01 to 2021-01-31 (Bible §20.1 admits "a fixed historical export"). Every "scheduled run" sees byte-identical data; a cron job re-deriving the same frozen 92 days produces the same brief forever. There is no "freshness," no new anomaly to catch "before a human asks," no decision to be made "in <5 minutes." The product's heartbeat — the proactive scheduled run (Principle 5) — has nothing to beat against. The only anomalies Helios will ever "catch" are the ones the eval harness *injects into a clone* (§20.2). So the headline differentiator versus Amplitude/Mixpanel ("autonomous, not pull") is demonstrated exclusively on synthetic perturbations the system planted itself. There is no artifact in this repo that can show the autonomous loop delivering value on real movement.

**Fundamental.** Static data cannot exhibit autonomy value.

---

### [CRITICAL] revenue-at-risk is a counterfactual resting on a false persistence assumption, then sold as a hard dollar number

**Claim attacked.** Glossary "Revenue-at-risk": "dollars recoverable if a degraded rate returned to its t0 / forecast baseline (≈ Δrate × affected sessions × downstream value)." §4.7: every finding "carries… a dollar revenue-at-risk." §5.4 lists "Dollar at-risk surfaced" as a business metric.

**Why it fails.** The formula assumes the t0 rate *would have persisted* absent the change — a counterfactual that is routinely false in e-commerce (post-holiday troughs, promo expiry, seasonal demand, mean reversion). The Bible knows this is fragile: §20.1 calls the labels "a *counterfactual*," and the dollar basis in scenarios.yaml (e.g. S001 "$38,000… (rate_t0 − rate_t1) × begin_checkout_sessions_t1 × aov") is computed *only because the injector knows the unperturbed truth.* On real data there is no unperturbed twin, so "revenue-at-risk" becomes "Δrate × volume × AOV holding everything else fixed" — a back-of-envelope figure dressed as a measured liability. Presenting `$72,000` (S024) to a Head of Growth as if it were a reconciled number, when it is the product of an unfalsifiable persistence assumption, is the kind of false precision that destroys analyst trust the first time the "recovered" dollars never appear.

**Fundamental.** No counterfactual is observable in production.

---

### [HIGH] The 85%-vs-45% benchmark is a unit test of the system's own arithmetic, not a measure of diagnostic skill

**Claim attacked.** §5.6/§20: "root-cause accuracy ≥85% (vs ≤45% naive baseline)" — "the project's central empirical claim" (§20.5). §24.1 pitch and §25.2 resume both lead with "85%+… vs 45%."

**Why it fails.** The injector perturbs aggregates using the *same* mix/rate/interaction algebra Decompose uses to diagnose (§20.2: "the *true* mix/rate/interaction contributions computed analytically by the same decomposition algebra Helios is graded on"). The "ground truth" and the "diagnosis" are the same equation run forward then backward. Scoring 85% on this is not evidence of analytical accuracy; it is a check that the arithmetic is implemented without bugs — a property a 20-line pandas function would also have. Worse, the ≤45% baseline ("largest absolute segment delta," §20.5) is a deliberately chosen strawman: no competent analyst declares a root cause from a single absolute delta without normalizing by rate. The "near-doubling" headline (§20.5) is the distance between a correct calculator and a calculator someone broke on purpose. As a *product* claim ("85% accurate diagnosis"), this number means almost nothing about whether real briefs are correct or trusted.

**Fundamental.** Ground truth is defined by the system under test.

---

### [HIGH] Mix-vs-rate decomposition does not deserve to be THE centerpiece — it is one routine technique every analyst owns

**Claim attacked.** §4.2: "The wedge is one painful, high-frequency, expensive job… automated mix-vs-rate root-cause diagnosis." §2.3 / Glossary: the decomposition is "Helios's technical centerpiece." §24.6 whiteboard: `ΔR = mix + rate + interaction`.

**Why it fails.** Mix/rate (a.k.a. attribution analysis, contribution decomposition, the "shift-share" method) is standard analyst toolkit — a GROUP BY plus a weighted-average identity. It is taught, scripted, and shipped inside existing tools (Amplitude/Mixpanel segmentation, GA4 "Insights" anomaly + contribution, any analyst's notebook). Building an entire seven-agent, five-MCP-server, 25-section system around one well-known identity is a category error: it elevates a *technique* to a *product*. The Bible itself concedes the technique is insufficient — §23.5 defers "true causal inference," "uplift modeling," and "double-ML" to Phase 4 with the admission that P1–P2 ship only "correlational decomposition." So the centerpiece is explicitly the *weakest* form of the analysis, and the genuinely hard parts (causality) are roadmap. A Head of Growth will not adopt a new "category" for a calculation their analyst already does in an afternoon.

**Fundamental.** A known identity cannot anchor a new category.

---

### [HIGH] The "insight-to-action gap" is misdiagnosed — Helios automates RCA but not the decide/prioritize/ship that actually gates action

**Claim attacked.** §2.1: "The gap between 'we see a number moved' and 'we changed the business' is the single most expensive inefficiency in growth analytics. Helios targets that gap directly." §1.6: "demonstrably shortens the insight-to-action loop from weeks to a single review cycle."

**Why it fails.** The insight-to-action gap is rarely bottlenecked on *generating* the RCA. It is bottlenecked on organizational decisioning: getting eng capacity allocated, prioritizing against the roadmap, securing stakeholder buy-in, and actually *shipping* the fix. Helios does none of that — it stops at a Decision Brief and an experiment it cannot run (§21 intro: "there is no live traffic to A/B test against"). It hands a PDF to the same humans who were already the bottleneck, now with more findings to triage. The §1.3 "AFTER" diagram ends at "decision made in <5 minutes of human reading time" — but reading is not deciding, and a brief is not a shipped change. By over-producing diagnoses (every scheduled run, every metric, every segment) Helios risks *widening* the action gap with alert volume, which is precisely why it needs a suppression list (FR-B4) — a band-aid for a firehose the product itself creates.

**Fundamental.** The named bottleneck is downstream of what Helios builds.

---

### [HIGH] The ROI story ("days to minutes") assumes RCA volume is the cost driver; it isn't

**Claim attacked.** §2.2: manual RCA is "~1–3 analyst-days" per anomaly, "the exact work Helios automates to a <5 min/run autonomous process." §5.2 baseline "~1–3 analyst-days (manual)" → target "<5 min/run."

**Why it fails.** This is a table of unsourced, self-serving estimates ("typical effort," "frequently never done") engineered to make the savings look enormous. Two problems. (1) The "1–3 days" is per *deep* RCA; most metric wiggles need a 10-minute glance, not 3 days, so multiplying by "metrics × segments × weeks" (§2.2) inflates a denominator that doesn't exist. (2) Even granting the saving, analyst *RCA hours* are not the dominant cost in a growth org — eng time on the fix, experiment runtime, and opportunity cost dwarf it. Automating the cheap step (find the segment) while leaving the expensive steps (build, test, ship) untouched is classic ROI theater. And the "<5 min/run" target is itself unmeasured (status: no code built), so the entire before/after comparison is target-vs-target.

**Fixable.** Re-scope ROI to measured cost drivers.

---

### [HIGH] The experiment-design framework prescribes tests the dataset can never run, and proves its own backlog is mostly impractical

**Claim attacked.** §4.1/§21: "prescribes a prioritized, statistically-defensible experiment backlog." §3.2 Marcus: "design the experiment." Every scenario's `expected_recommendation` ends "Size via power_analysis."

**Why it fails.** §21 admits the data is "OBSERVATIONAL and historical — there is no live traffic to A/B test against," then the §21.2 worked example computes that the flagship card H-2021-0042 needs ~14,800 sessions/arm against ~95/day → **311 days → UNDERPOWERED**. The product's signature output (a powered experiment) is, by its own math, un-runnable at the segment grain where its diagnoses live. The fallback (§21.2: "roll up to a coarser segment… or relax mde") destroys the very segment-precision the decomposition spent seven agents establishing. So Prescribe ships hypothesis cards (scenarios.yaml: "A/B test a sticky mobile add-to-cart button," "expedited guest-checkout") that no one can execute on this data, sized for a funnel that no longer receives traffic. A backlog of un-runnable experiments "ranked by money" (§21.4 ICE) is a vanity artifact, and the quasi-experimental DiD fallback (§21.5) is circular here because the only "treatment" is the injection the harness applied.

**Fundamental.** Observational static data forecloses experimentation.

---

### [MEDIUM] Persona realism: no Head of Growth overrides their analyst on an autonomous AI's dollar figure

**Claim attacked.** §3.1 Priya: "Success criteria: Time-to-diagnosis <5 min reading; ≥85% of root causes correct." §24.3(a) STAR: "the decomposition gave an auditable answer that overrode the gut call on checkout." §3.1 anti-needs: "does NOT want… a chatbot to interrogate."

**Why it fails.** The persona is constructed to want exactly what Helios outputs and to reject exactly what it doesn't build (a chatbot, raw tables). That is reverse-engineered, not observed. In reality a Head of Growth who is "chronically time-poor" and "reports to the exec team weekly" will *not* forward a CEO a `$72,000 revenue-at-risk` from an unsupervised LLM without her analyst sanity-checking it first — which reintroduces the human RCA loop the product claims to remove, and means the analyst (Dana) must now *audit Helios* on top of her old job. The §3.1 claim that Priya wants no interrogation surface contradicts trust-building: the first time a brief is wrong (and on real exogenous causes it will be — see Critical #1), she will demand to drill in, i.e. demand the chatbot the anti-product (§4.4) forbids. The personas assume trust that the product has not earned and structurally cannot earn on causal claims.

**Fixable.** Personas can be re-grounded in real buying behavior.

---

### [MEDIUM] Category/moat claim ("creates a new category") ignores shipped incumbents doing the same job

**Claim attacked.** §1.2: "It creates a new category: **autonomous growth diagnosis**." §2.5: "None of them autonomously decompose mix-vs-rate, price the movement, and ship a verified brief on a schedule. That white space… is precisely Helios's category."

**Why it fails.** The "white space" is asserted, not evidenced, and is largely already occupied. GA4 itself ships automated anomaly detection with contribution analysis and emailed Insights *on a schedule*; Amplitude and Mixpanel ship anomaly alerts, automated root-cause / "Compass" style contribution, and AI summaries. The Bible's own comparison table (§1.2) concedes Amplitude/Mixpanel answer "What, with some who" and have "recent 'AI' features" (§2.5) — then waves them away as "still fundamentally descriptive." But pricing the movement in dollars and emailing a segmented contribution breakdown is not a new *category*; it is a feature delta over incumbents who have distribution, integrations, and live data Helios lacks. "Creating a category" is a resume/interview framing (§24, §25) not a defensible moat — there is no proprietary data, no network effect, and the core technique is public-domain arithmetic.

**Fixable.** Reframe as a feature, drop the category claim.

---

### [MEDIUM] The success metrics are dominated by vanity/leading proxies, not decision-grade outcomes

**Claim attacked.** §5.2 lists seven "product-quality" metrics, all "Leading"; the North Star (§5.1) is "Verified, actioned Decision Briefs that correctly diagnose root cause," but the *measurable* lagging outcomes (§5.4: "Decisions influenced," "Misdiagnosis cost avoided," "Experiments shipped") are exactly the ones the static dataset makes unobservable.

**Why it fails.** "0 hallucinated columns," "100% governed SQL," "100% findings carry significance + $," "scheduled-run completion rate" (§5.3) are all *process compliance* metrics — they measure that the plumbing ran, not that any decision improved. They are trivially satisfiable (a system that always emits the same governed query and the same dollar formula scores 100% on every one) and tell a buyer nothing about value. Meanwhile the only metrics that would prove the thesis — decisions influenced, misdiagnosis cost avoided, experiments shipped and won (§5.4, all "Lagging") — are uninstrumentable on a frozen 3-month sample with no users and no action-tracking signal. So the dashboard of "success" is entirely the vanity column, and the North Star's "actioned" and "influence a decision" clauses are, on this data, permanently unmeasurable. A product whose only measurable metrics are the ones that don't matter is optimizing the wrong loop.

**Fixable.** Promote decision-grade outcomes; demote compliance proxies.
