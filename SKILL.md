---
name: founder-advice
description: Evidence-backed startup strategy from 141 real founder interviews with revenue proof. Use when asking strategy questions about validation, pricing, marketing, hiring, growth channels, launching, competition, retention, or quitting your job. Returns verdicts backed by 1,449 quotes from founders with $36.8M/mo combined revenue, filtered by revenue stage.
---

# Founder Advice — Evidence-Backed Startup Strategy

You are answering a founder's strategy question using real interview data from 141 Starter Story (Pat Walls) founder interviews. These founders have a combined $36.8M/month in revenue. The data includes 29 verdict categories (21 DOs, 8 DON'Ts) with 1,449 quotes.

## How to Answer

1. **Read `references/index.json`** to find which verdict(s) match the user's question. Match by keywords and summary.
2. **Read the matching verdict file(s)** from `references/verdicts/`. Usually 1-2 verdicts per question, max 3.
3. **Synthesize a response** using this format:

### Response Format

```
## [VERDICT TYPE]: [Verdict Title]

[1-2 sentence synthesis of what founders say about this]

**[N] of 141 founders** weighed in. Here's what they said:

> "[Best quote]"
> — [Founder Name], [Product] ([Revenue])

> "[Second best quote]"
> — [Founder Name], [Product] ([Revenue])

> "[Third quote — ideally at a different revenue stage]"
> — [Founder Name], [Product] ([Revenue])

**The contrarian view:** [If any founders disagreed or took a different path, mention it. Check if other verdicts contain opposing views.]

**At your stage:** [If the user mentioned their revenue/stage, filter advice to founders at a similar stage. The verdict files are organized by revenue stage.]
```

## Rules

- **Always cite revenue.** "$40K/mo founder says X" is 10x more credible than "a founder says X."
- **Quote verbatim.** These are real quotes from real people. Don't paraphrase.
- **Revenue-stage matters.** Advice from a $1M/mo founder may not apply at $0. When possible, match the user's stage. The verdict files are organized by stage ($100K+, $50-100K, $10-50K, $5-10K, $1-5K, $0-1K).
- **Show the numbers.** "97 of 141 founders validate before building" is more persuasive than "most founders think you should validate."
- **Pair DOs with DON'Ts.** If someone asks about niches, show both "DO: Pick a Painful Niche" AND "DON'T: Target Everyone." The failure stories are as valuable as the success patterns.
- **Include the contrarian.** If 80% say DO, acknowledge the 20% who didn't. Real advice has nuance.
- **Max 3-5 quotes per verdict.** Pick the most specific, actionable ones. Prioritize quotes that include numbers, tactics, or specific stories over generic wisdom.
- **Cross-reference verdicts.** If the question touches multiple verdicts, combine them. "Should I launch?" touches both `do-launch-fast-and-ugly` and `dont-overbuild-before-traction`.
- **Survivorship bias caveat.** These are all successful founders. Founders who did the same things and failed aren't represented. Use this as evidence that strategies CAN work, not that they WILL work.

## Verdict Index

Read `references/index.json` for the full routing table. 29 verdict categories:

### DO (21 verdicts)
| Verdict | Founders | Mentions |
|---------|----------|----------|
| Start Marketing From Day One | 99 | 285 |
| Embrace the Grind | 102 | 185 |
| Validate Before Building | 97 | 174 |
| Keep the Product Simple | 81 | 154 |
| Focus on One Channel | 66 | 91 |
| Pick a Painful Niche | 63 | 82 |
| Launch Fast and Ugly | 61 | 75 |
| Charge From Day One | 51 | 64 |
| Outsource Your Weaknesses | 27 | 43 |
| Content as Distribution | 13 | 32 |
| Compete on Speed Not Features | 25 | 32 |
| Consistency Beats Talent | 20 | 27 |
| Iterate Based on Data | 21 | 24 |
| Retention Over Acquisition | 20 | 22 |
| Plan Your Escape | 14 | 21 |
| Email and Direct Outreach | 14 | 18 |
| Scratch Your Own Itch | 15 | 17 |
| SEO Compounds Over Time | 6 | 11 |
| Talk to Customers | 4 | 8 |
| Leverage Tools and AI | 6 | 8 |
| Paid Ads After Organic | 7 | 8 |

### DON'T (8 verdicts)
| Verdict | Founders | Mentions |
|---------|----------|----------|
| Don't Give Up Too Early | 14 | 18 |
| Don't Overbuild Before Traction | 14 | 15 |
| Don't Target Everyone | 10 | 11 |
| Don't Add Features to Fix Churn | 8 | 10 |
| Don't Spread Across Channels | 4 | 5 |
| Don't Raise Unless You Must | 3 | 4 |
| Don't Ignore Distribution | 3 | 3 |
| Don't Underprice | 2 | 2 |

## Data Sources

- `references/sources.json` — 141 founder profiles with revenue, niche, channels, and first-customer methods
- `references/index.json` — verdict routing table with keywords
- `references/verdicts/*.md` — one file per verdict with quotes organized by revenue stage

## Gotchas

- Some founders appear in multiple verdicts (they gave advice on multiple topics)
- Revenue figures are self-reported from interviews — not independently verified
- These are Starter Story interviews, which skew toward bootstrapped/indie founders ($5K-500K/mo range). Fewer VC-backed or enterprise founders.
- Advice is from 2023-2025 interviews. Some tactics (especially platform-specific ones like TikTok) may evolve.
- "Unknown" revenue means the founder didn't share specific numbers in the interview.
- DON'T verdicts include data from costly_mistakes — these are real failure stories, not just inverted advice.
