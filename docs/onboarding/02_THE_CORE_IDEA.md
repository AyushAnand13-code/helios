# 2. The one idea you must own: mix-shift vs rate-change

If you remember nothing else, remember this. It's the heart of the project, it's a genuinely
senior analytics concept, and it's what makes interviewers nod.

## The trap (Simpson's paradox)
A store's **overall conversion rate** can drop **even when every single customer segment got
better or stayed the same.** How? Because the *mix* of traffic changed.

A naïve analyst sees "overall conversion down 10%" and says "the checkout must be broken —
let's fix it." Sometimes that's right. Sometimes the checkout is perfectly fine and they're
about to waste weeks chasing a ghost. Helios tells the two apart.

## A worked example with real numbers
A store gets traffic from **desktop** (converts well, 4%) and **mobile** (converts worse, 2%).

**Week 1** — traffic is split 50/50:
```
desktop:  50% of visits × 4% conversion = 2.0
mobile:   50% of visits × 2% conversion = 1.0
                          OVERALL conversion = 3.0%
```

Now two different things could happen in **Week 2**, and they look almost identical on the
surface:

### Case A — a MIX-shift (composition changed, nobody's behaviour changed)
A marketing campaign brings a flood of cheap mobile traffic. Now it's 30% desktop / 70%
mobile. **Each device still converts exactly as before (4% and 2%).**
```
desktop:  30% × 4% = 1.2
mobile:   70% × 2% = 1.4
              OVERALL = 2.6%   ← dropped from 3.0% to 2.6%
```
Overall conversion fell, but **nothing is broken.** Desktop is still 4%, mobile is still 2%.
"Fixing the checkout" would do nothing. The real lever is **acquisition** — you bought a lot
of low-intent mobile traffic.

### Case B — a RATE-change (real behaviour got worse)
Traffic mix is unchanged (still 50/50), but a checkout bug means **each device actually
converts worse** (desktop 3.5%, mobile 1.8%):
```
desktop:  50% × 3.5% = 1.75
mobile:   50% × 1.8% = 0.90
              OVERALL = 2.65%   ← also dropped to ~2.6%
```
Same headline drop — but this time something **is** broken, and you should investigate the
funnel/UX.

### The punchline
Both cases show "overall conversion dropped from 3.0% to ~2.6%." **The headline number is
identical. The correct action is the opposite.** Case A → fix acquisition/marketing.
Case B → fix the product/checkout. Get it wrong and you waste the team's time.

## How Helios separates them (the decomposition)
Helios splits **every** change in an overall rate into three additive pieces:

- **mix effect** — how much of the change came from the *composition* shifting (Case A).
- **rate effect** — how much came from *in-segment behaviour* actually changing (Case B).
- **interaction** — the small bit where both moved together.

These three always add up exactly to the total change. Helios then **drills into the rate
effect** (the real, actionable behaviour change) and **ignores the mix effect** (a
composition artifact, not a bug).

> **Interview line:** *"Helios decomposes every aggregate move into mix, rate, and interaction
> components — so it never tells you to fix the checkout when really your traffic mix just
> shifted toward mobile. That's the Simpson's-paradox defense, and it's the core of the
> project."*

## Where this lives in the code
`helios/stats/decompose.py` — about 100 lines of real math (`decompose_change`). It's
**golden-tested**: there are unit tests with hand-worked numbers that pin the exact mix/rate
values, so a future change can't silently break it. The formula:
```
mix_effect   = Σ (Δweight_i × rate_i)      # the segment's share of traffic changed
rate_effect  = Σ (weight_i × Δrate_i)      # the segment's own conversion changed
interaction  = Σ (Δweight_i × Δrate_i)     # both moved together
total change = mix_effect + rate_effect + interaction
```
(Σ just means "sum over all the segments," like desktop and mobile.)

## Why this impresses interviewers
- It's a real statistics concept (Simpson's paradox) most candidates can't implement.
- It maps directly to a **business mistake worth real money** (fixing the wrong thing).
- It shows you think about *causes and actions*, not just dashboards.

Next: **[03_THE_DATA.md](03_THE_DATA.md)** — where the data comes from and what the tables are.
