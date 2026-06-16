# 1. What Helios is (plain English)

## The problem it solves
Imagine you run the online Google Merchandise Store. Every week, someone asks:

> *"Our conversion rate dropped this week. **Why?** Is something broken? Are we losing money?
> What should we do about it?"*

Normally a **data analyst** spends a day on this: pulling data, slicing it by device and
channel, arguing about whether the drop is real or just noise, estimating the dollar impact,
and writing it up. It's slow, manual, and easy to get wrong (more on the "getting it wrong"
part in [02_THE_CORE_IDEA.md](02_THE_CORE_IDEA.md)).

## What Helios does
Helios is a program that does that analyst's job **automatically, every day**. Given the
store's web-analytics data, it:

1. **Notices** when a funnel metric (like conversion rate) moves more than expected.
2. **Explains why** — and crucially, tells apart two very different causes (a real behaviour
   change vs. a statistical illusion caused by the *type* of traffic changing).
3. **Checks itself** — runs the move through statistical tests and a "Critic" that tries to
   prove the finding wrong before trusting it.
4. **Prices it** — "this is about **$7,500 of revenue at risk** this week."
5. **Prescribes an action** — including a ready-to-launch **A/B test**, correctly sized.
6. **Writes it up** as a short executive **Decision Brief**.

It's "autonomous" because it runs on a schedule on its own (a daily job), not only when a
human clicks a button.

## The "sales funnel" it analyses
A **funnel** is the steps a shopper goes through. Each step loses some people:

```
visited the site → viewed a product → added to cart → started checkout → paid
   (100%)              (60%)              (30%)            (15%)          (2%)
```

If fewer people make it to "paid" this week, Helios figures out **which step** leaked and
**why**.

## A concrete example (what it actually output, on real data)
On the real Google Analytics dataset, Helios produced:

> *Session conversion dropped **1.64% → 1.06%** week-over-week (−0.59 points). This is
> statistically significant (p ≈ 0.00000001). The dominant cause is a **rate-change**
> (real behaviour), concentrated in **Referral / desktop** and **Referral / mobile** traffic.
> Revenue at risk: **−$7,538**. Recommended action: investigate the checkout experience for
> those segments. Critic verdict: SHIP.*

Every number there came from a real calculation on real data — the AI wrote the sentences,
not the numbers.

## The two pitches (memorise these)

**30-second version (for "tell me about a project"):**
> *"I built Helios — an autonomous growth-diagnosis engine. Every day it looks at an
> e-commerce store's web-analytics funnel, figures out **why** conversion moved, separates a
> real behaviour change from a traffic-mix illusion, prices it in revenue-at-risk, and
> proposes a sized A/B test — then writes an executive brief. It runs on the real public
> Google Analytics dataset, and it's built so the AI can never invent a number: all the SQL
> and all the statistics come from governed, tested code, and an automated 'Critic' checks
> every finding before it ships."*

**2-minute version:** the 30-second pitch, then walk through the example above, then say:
> *"The hardest part is a statistics concept called Simpson's paradox — a store's overall
> conversion can drop even when every customer segment got better, just because the mix of
> traffic shifted. Most analysts get this wrong and 'fix the checkout' when the checkout is
> fine. Helios decomposes every change into 'mix' vs 'rate' to avoid exactly that mistake.
> I verified the whole thing runs on real Google Analytics data, and I used Claude Code to
> build it fast while making the architecture and grounding decisions myself."*

Next: **[02_THE_CORE_IDEA.md](02_THE_CORE_IDEA.md)** — the one idea you must be able to explain.
