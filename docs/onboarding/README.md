# Understand Helios — start here

This folder explains the **whole project from zero**, in plain English, for someone who has
not used dbt, BigQuery, or MCP before. Read it in order; by the end you'll be able to
explain every part of Helios in an interview and answer follow-up questions.

**Read in this order:**

1. **[01_START_HERE.md](01_START_HERE.md)** — what Helios is, in one breath, with a real
   example. The 30-second / 2-minute pitches.
2. **[02_THE_CORE_IDEA.md](02_THE_CORE_IDEA.md)** — *mix-shift vs rate-change* with a worked
   number example. **This is the one concept you must own.**
3. **[03_THE_DATA.md](03_THE_DATA.md)** — what GA4, BigQuery, and dbt are, and what each
   table means. (No prior knowledge assumed.)
4. **[04_THE_ARCHITECTURE.md](04_THE_ARCHITECTURE.md)** — the full pipeline end-to-end, what
   "MCP servers" and "agents" actually are, and why each piece exists.
5. **[05_THE_DASHBOARD.md](05_THE_DASHBOARD.md)** — a walkthrough of every box, number, and
   chart on the Streamlit dashboard, and what to *say* about each.
6. **[06_GLOSSARY.md](06_GLOSSARY.md)** — every piece of jargon decoded, with the one-line
   interview phrasing for each.
7. **[07_INTERVIEW_PLAYBOOK.md](07_INTERVIEW_PLAYBOOK.md)** — role-specific pitches
   (analytics / consulting / data science), hard Q&A, a demo script, how to talk about
   using Claude Code, and how to genuinely *own* the project.

> **The honest framing in one line:** *Helios is an "always-on AI growth analyst" that, every
> day, figures out **why** an online store's sales funnel moved, tells a real change apart from
> a statistical illusion, prices it in dollars, and proposes an A/B test — all on real Google
> Analytics data, with guardrails so the AI can't make numbers up.*
