# 7. Interview playbook — present it, own it

You're targeting **analytics, consulting, and data-science** roles, and you want to show you can
use **Claude Code** well. This is how to do all three honestly.

---

## A. The pitch at three lengths

**10 seconds (one breath):**
> *"I built an autonomous 'AI growth analyst' that diagnoses why an e-commerce funnel moved —
> on real Google Analytics data — and proposes a fix, with guardrails so the AI can't fabricate
> numbers."*

**30 seconds:** (the version in [01_START_HERE.md](01_START_HERE.md) — memorise it.)

**2 minutes:** 30-second pitch → the mix-vs-rate example with numbers (doc 02) → "it runs on the
real public GA4 dataset, the dbt models build green, and the LLM is grounded so every figure
traces to a tested tool" → "I used Claude Code to build it fast while making the architecture and
correctness decisions myself."

---

## B. Tailor it to the role

**Analytics / Analytics Engineering**
- Lead with: the **dbt star schema** (staging → sessionization → fact/dim marts), the **semantic
  layer** (single source of truth for metrics), and **data tests** (funnel monotonicity, revenue
  reconciliation). 
- Lead with the **mix-vs-rate decomposition** as the analytical centrepiece.
- Phrase: *"It's a governed analytics stack — one definition per metric, tested transforms, and a
  decomposition that avoids the classic Simpson's-paradox mistake."*

**Consulting**
- Lead with the **business framing**: it turns "conversion dropped" into "here's *why*, here's the
  **dollar impact**, here's the **action**, and here's the **experiment** to validate it."
- Emphasise the **mix-vs-rate insight** as "don't fix the checkout when the real issue is your
  traffic mix" — a costly mistake it prevents.
- Phrase: *"It's structured like a consulting deliverable: diagnosis → quantified impact →
  recommendation → a way to test it — produced automatically and defensibly."*

**Data Science**
- Lead with the **statistics**: the additive mix/rate/interaction decomposition, the **two-
  proportion z-test** for significance, **power analysis** for experiment sizing, and **forecast-
  based anomaly detection**.
- Emphasise **rigor & reproducibility**: seeded deterministic math, golden unit tests, an offline
  benchmark, and a CI gate.
- Phrase: *"The math is all real and tested — decomposition, significance, power analysis,
  forecasting — and there's an offline benchmark with a CI quality gate."*

**(Any role) the AI-engineering angle**
- The **grounding** design (LLM never writes SQL/does math), the **MCP tool architecture**, the
  **Critic** (verify-then-trust), and **per-agent allow-lists**. This shows you can build AI
  systems *responsibly* — a hot, senior topic.

---

## C. How to talk about using Claude Code (own it honestly)

You used an AI coding tool. That's a **strength**, if you frame it as *you directing the work*:

- **Do say:** *"I used Claude Code as a pair-programmer to move fast, but I made the architecture
  and correctness calls — the data model, the grounding rules, what the Critic checks, how the
  decomposition works. I verified everything: I ran the dbt build and the full pipeline against
  real BigQuery myself, and I read and understood every component."*
- **Show ownership with specifics** — these prove you understand it:
  - *"I caught a real bug: a refactor changed the source table from `fct_daily_funnel` to
    `fct_funnel` and silently broke the dashboard's data path — I diagnosed it and added a
    session-grain synthetic table that reconciles exactly."*
  - *"I found a dbt config mismatch — per-folder configs weren't applying because of how
    `model-paths` was set — and fixed the schema routing so marts land in the right dataset."*
- **Don't** pretend you hand-typed every line, and **don't** let it sound like the AI did it
  alone. The truth — *"I architected and verified; AI accelerated the typing"* — is both honest
  and impressive. Modern teams *want* people who can direct AI tools well.

> **Interview line:** *"Using Claude Code well is itself a skill I wanted to demonstrate — turning
> a clear architecture and quality bar into a working, tested system quickly, while keeping
> ownership of every decision."*

---

## D. The live demo script (5 minutes)
1. `dbt build --profiles-dir .` → *"This builds the whole data layer from real GA4 — PASS=62,
   every test green."*
2. `python -m helios.run --source bigquery --no-memory` → *"The autonomous run: one command,
   real data, out comes a dated Decision Brief — here's the conversion drop, the dollar impact,
   the cause, the Critic verdict."*
3. `python -m helios.run --orchestrated` → *"Same thing through the 7-agent pipeline — note the
   tool trace and the allow-list enforcement."*
4. `streamlit run app.py` → walk the **mix-vs-rate chart**, the **Critic panel**, the **powered
   experiment**, and the **grounded AI brief** (open the grounding panel). Use doc 05 for what to
   say at each.

---

## E. Hard questions + honest answers

- **"Is this real or a toy?"** → *"Real. It runs on the public GA4 e-commerce dataset — 4.3M
  events — the dbt spine builds green (PASS=62), and I've run the governed pipeline and the LLM
  brief against live BigQuery."*
- **"How do you know the LLM didn't make up the numbers?"** → *"It can't — it only calls governed
  tools, and the brief shows the grounding trace. I verified the LLM's figures matched the
  deterministic engine exactly."*
- **"What's your eval / how accurate is it?"** → *"On a 50-scenario benchmark it recovers the
  injected cause with zero hallucinated metrics, and beats a naïve baseline that's blind to
  mix-shifts. Honest caveat: that's controlled-attribution accuracy on synthesized scenarios —
  it proves recovery and guards against regressions; it's not a claim of real-world causal
  accuracy."*
- **"Are these really autonomous AI agents?"** → *"It's a deterministic role-based pipeline with
  enforced per-agent tool permissions and a Critic gate — not autonomous LLM agents. The next
  step is promoting it to the Claude Agent SDK."*
- **"What was hard?"** → tell a real bug story (the `fct_funnel` regression or the dbt config
  mismatch). These land well because they're specific and true.
- **"What would you do next?"** → *"Cohort/retention and RFM analyses, forecast-driven monitoring
  on more metrics, and true LLM agents via the Agent SDK."*

---

## F. The "own it" study plan (do before interviews)
1. Read docs **01 → 06** in this folder, in order. Then re-read **02** until you can teach the
   mix-vs-rate example from memory with the numbers.
2. Run the demo (section D) yourself once, end to end, watching each output.
3. Open three files and read them — they're short and you should recognise them:
   `helios/stats/decompose.py` (the core math), `helios/critic.py` (the checks),
   `semantic/semantic_layer.yaml` (a couple of metric definitions).
4. Practise the 30-second and 2-minute pitches out loud.
5. Memorise the **honesty caveats** (what NOT to claim) — they're what make you credible.

You built something real, on real data, with genuine analytics and AI-systems thinking, and you
can explain every layer. Lead with the mix-vs-rate idea, stay honest about the caveats, and own
the decisions. You've got this.
