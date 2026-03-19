#!/usr/bin/env python3
"""
Build verdict files from extracted founder advice.
1. Cluster 63 raw categories into ~20 clean verdict groups
2. Generate one markdown file per verdict in references/verdicts/
3. Build index.json (routing metadata) and sources.json (video metadata)
"""
import json
import os
import re
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTIONS_FILE = os.path.join(BASE_DIR, "data", "extractions.json")
VERDICTS_DIR = os.path.join(BASE_DIR, "references", "verdicts")
REFS_DIR = os.path.join(BASE_DIR, "references")

os.makedirs(VERDICTS_DIR, exist_ok=True)
os.makedirs(REFS_DIR, exist_ok=True)

# --- Category → Verdict mapping ---
# Maps raw extraction categories to clean verdict slugs
# We use quote text matching for categories that need splitting (marketing, mindset, product)
# For those, the category is mapped to a "SPLIT:" prefix — handled in cluster_quotes()
CATEGORY_MAP = {
    # Validation — split: validate vs scratch-own-itch
    "validation": "SPLIT:validation",
    "idea-generation": "do-scratch-your-own-itch",
    "ideation": "do-scratch-your-own-itch",
    "market-opportunity": "do-validate-before-building",

    # Niche selection — split: do pick niche vs don't target everyone
    "niche-selection": "SPLIT:niche",

    # Launch & shipping — split: launch vs iterate
    "launch": "do-launch-fast-and-ugly",
    "iteration": "do-iterate-based-on-data",
    "planning": "do-launch-fast-and-ugly",

    # Product — split: simple vs overbuild vs tools
    "product": "SPLIT:product",
    "tools": "do-leverage-tools-and-ai",
    "ai-tools": "do-leverage-tools-and-ai",
    "vibe-coding": "do-leverage-tools-and-ai",
    "analytics": "do-iterate-based-on-data",
    "metrics": "do-iterate-based-on-data",

    # Marketing — split: organic vs paid vs distribution-first vs ignore-distribution
    "marketing": "SPLIT:marketing",
    "paid-ads": "do-paid-ads-after-organic",
    "email-marketing": "do-email-and-direct-outreach",
    "distribution": "SPLIT:distribution",

    # Content & SEO — merge build-in-public into content
    "content": "do-content-as-distribution",
    "SEO": "do-seo-compounds-over-time",
    "writing": "do-content-as-distribution",
    "audience-building": "do-content-as-distribution",
    "build-in-public": "do-content-as-distribution",

    # Growth — split: focus channel vs don't spread thin
    "growth": "SPLIT:growth",
    "networking": "do-focus-on-one-channel",
    "partnerships": "do-focus-on-one-channel",
    "partnership": "do-focus-on-one-channel",

    # Pricing — split: charge early vs don't underprice
    "pricing": "SPLIT:pricing",
    "monetization": "do-charge-from-day-one",
    "conversion": "do-charge-from-day-one",
    "business-model": "do-charge-from-day-one",

    # Mindset — split: grind vs consistency vs dont-give-up
    "mindset": "SPLIT:mindset",
    "persistence": "dont-give-up-too-early",
    "consistency": "do-consistency-beats-talent",
    "habits": "do-consistency-beats-talent",
    "focus": "do-consistency-beats-talent",
    "business-focus": "do-consistency-beats-talent",
    "routine": "do-consistency-beats-talent",
    "productivity": "do-consistency-beats-talent",
    "learning": "do-embrace-the-grind",
    "skill-building": "do-embrace-the-grind",
    "mentorship": "do-embrace-the-grind",

    # Hiring & Team
    "hiring": "do-outsource-your-weaknesses",
    "outsourcing": "do-outsource-your-weaknesses",
    "management": "do-outsource-your-weaknesses",
    "operations": "do-outsource-your-weaknesses",
    "negotiation": "do-outsource-your-weaknesses",

    # Competition — split: speed vs don't compete on price
    "competition": "SPLIT:competition",
    "positioning": "do-compete-on-speed-not-features",
    "branding": "do-compete-on-speed-not-features",
    "strategy": "do-compete-on-speed-not-features",

    # Retention — split: do retention vs don't add features to fix churn
    "retention": "SPLIT:retention",
    "customer-support": "do-retention-over-acquisition",

    # Quitting job / Going full-time
    "quitting-job": "do-plan-your-escape",
    "bootstrapping": "do-plan-your-escape",
    "solo-founder": "do-plan-your-escape",
    "funding": "dont-raise-unless-you-must",
    "investing": "dont-raise-unless-you-must",
    "investment": "dont-raise-unless-you-must",
    "diversification": "do-plan-your-escape",

    # Sales & customers
    "sales": "do-talk-to-customers",
    "timing": "do-talk-to-customers",

    # Scaling → fold into overbuild
    "scaling": "dont-overbuild-before-traction",
}

# Keywords for splitting large categories into DO/DON'T pairs
SPLIT_KEYWORDS = {
    "SPLIT:validation": {
        "do-scratch-your-own-itch": ["own problem", "own itch", "my own", "myself", "personal", "I needed", "I wanted", "I was frustrated", "my experience", "solving my"],
        "do-validate-before-building": None,  # default
    },
    "SPLIT:niche": {
        "dont-target-everyone": ["everyone", "too broad", "broad audience", "general", "nobody", "no one", "too many", "all people", "mass market", "generic", "unfocused", "wide net"],
        "do-pick-a-painful-niche": None,  # default
    },
    "SPLIT:product": {
        "dont-overbuild-before-traction": ["too many features", "overbuilt", "over-engineer", "spent too long", "wasted time", "too complex", "nobody used", "didn't need", "feature creep", "gold plat", "scope creep", "months building", "year building", "before anyone"],
        "do-keep-product-simple": None,  # default
    },
    "SPLIT:marketing": {
        "do-paid-ads-after-organic": ["paid ads", "Facebook ads", "Google ads", "TikTok ads", "ad spend", "ROAS", "paid traffic", "paid acquisition", "cost per", "CPA", "CAC"],
        "do-email-and-direct-outreach": ["cold email", "cold outreach", "DM", "direct message", "outreach", "cold call", "email list", "newsletter"],
        "dont-ignore-distribution": ["didn't market", "no marketing", "forgot", "neglect", "built it and they", "if you build it", "nobody came", "zero traffic", "no users", "wish I had started marketing", "biggest mistake was not"],
        "do-marketing-from-day-one": None,  # default
    },
    "SPLIT:distribution": {
        "dont-ignore-distribution": ["didn't market", "no marketing", "forgot", "neglect", "built it and they", "if you build it", "nobody came", "zero traffic", "biggest mistake"],
        "do-marketing-from-day-one": None,  # default
    },
    "SPLIT:growth": {
        "dont-spread-across-channels": ["too many channels", "spread thin", "spread too thin", "every channel", "all channels", "dilut", "unfocused", "tried everything", "didn't focus"],
        "do-focus-on-one-channel": None,  # default
    },
    "SPLIT:pricing": {
        "dont-underprice": ["too cheap", "too low", "underpric", "raised the price", "doubled the price", "tripled", "10x", "should have charged more", "wasn't charging enough", "leaving money"],
        "do-charge-from-day-one": None,  # default
    },
    "SPLIT:mindset": {
        "dont-give-up-too-early": ["don't give up", "don't quit", "gave up", "quit too", "persist", "kept going", "didn't quit", "almost quit", "stick with", "years", "took time"],
        "do-consistency-beats-talent": ["consistent", "every day", "daily", "routine", "habit", "discipline", "show up", "compound", "long game", "patience"],
        "do-embrace-the-grind": None,  # default
    },
    "SPLIT:competition": {
        "dont-underprice": ["cheaper", "cheapest", "low price", "undercut", "race to the bottom", "price war", "lowest price"],
        "do-compete-on-speed-not-features": None,  # default
    },
    "SPLIT:retention": {
        "dont-add-features-to-fix-churn": ["more features", "added features", "feature", "churn", "leaving", "cancel", "didn't solve", "still churned", "wrong reason"],
        "do-retention-over-acquisition": None,  # default
    },
}

# Verdict display metadata
VERDICT_META = {
    "do-validate-before-building": {
        "title": "Validate Before Building",
        "type": "DO",
        "summary": "Talk to customers, check demand, get paid before writing code.",
        "keywords": ["validate", "idea validation", "market research", "customer discovery", "demand", "problem", "should I build"],
    },
    "do-scratch-your-own-itch": {
        "title": "Scratch Your Own Itch",
        "type": "DO",
        "summary": "Build something you personally need. You become the ideal user.",
        "keywords": ["own problem", "scratch itch", "personal pain", "I needed this", "build for yourself", "own experience"],
    },
    "do-pick-a-painful-niche": {
        "title": "Pick a Painful Niche",
        "type": "DO",
        "summary": "Narrow markets with real pain pay better than broad ones with mild annoyance.",
        "keywords": ["niche", "market", "target audience", "ICP", "vertical", "industry", "B2B vs B2C", "who to sell to"],
    },
    "do-launch-fast-and-ugly": {
        "title": "Launch Fast and Ugly",
        "type": "DO",
        "summary": "Ship the MVP in weeks, not months. Perfection is the enemy of traction.",
        "keywords": ["launch", "MVP", "ship", "perfect", "ready", "when to launch", "first version", "just ship"],
    },
    "do-iterate-based-on-data": {
        "title": "Iterate Based on Data, Not Gut",
        "type": "DO",
        "summary": "Let users and metrics tell you what to build next, not your instincts.",
        "keywords": ["iterate", "data", "analytics", "metrics", "A/B test", "feedback loop", "user data", "what to build next"],
    },
    "do-keep-product-simple": {
        "title": "Keep the Product Simple",
        "type": "DO",
        "summary": "Solve one problem well. Features don't win — solving pain does.",
        "keywords": ["simple", "features", "scope", "bloat", "complexity", "focus", "product", "over-engineering", "one thing"],
    },
    "do-leverage-tools-and-ai": {
        "title": "Leverage No-Code, AI, and Existing Tools",
        "type": "DO",
        "summary": "You don't need to build everything from scratch. Use what exists.",
        "keywords": ["no-code", "AI", "tools", "automate", "template", "Zapier", "ChatGPT", "vibe coding", "build faster"],
    },
    "do-marketing-from-day-one": {
        "title": "Start Marketing Before the Product is Ready",
        "type": "DO",
        "summary": "Marketing is not a phase — it's a habit. Start before you ship.",
        "keywords": ["marketing", "traffic", "acquisition", "promote", "how to get users", "growth channel", "marketing strategy"],
    },
    "do-paid-ads-after-organic": {
        "title": "Go Organic First, Paid Ads Second",
        "type": "DO",
        "summary": "Prove the message works organically before spending money on ads.",
        "keywords": ["paid ads", "Facebook ads", "Google ads", "TikTok ads", "ad spend", "ROAS", "organic first", "when to run ads"],
    },
    "do-email-and-direct-outreach": {
        "title": "Cold Email and Direct Outreach Still Works",
        "type": "DO",
        "summary": "DMs, cold emails, and direct outreach get your first customers faster than content.",
        "keywords": ["cold email", "outreach", "DM", "direct message", "cold outreach", "first customers", "email list", "newsletter"],
    },
    "do-content-as-distribution": {
        "title": "Use Content as Your Distribution Engine",
        "type": "DO",
        "summary": "Content marketing compounds. Create valuable content, attract an audience, convert to customers.",
        "keywords": ["content marketing", "blog", "social media", "Twitter", "YouTube", "TikTok", "content strategy"],
    },
    "do-seo-compounds-over-time": {
        "title": "SEO Compounds — Start Early",
        "type": "DO",
        "summary": "SEO takes months to kick in but becomes your best channel once it does.",
        "keywords": ["SEO", "search engine", "Google", "organic traffic", "keywords", "blog posts", "programmatic SEO", "long-term"],
    },
    "do-focus-on-one-channel": {
        "title": "Master One Channel Before Adding More",
        "type": "DO",
        "summary": "Founders who win go deep on one channel before spreading thin.",
        "keywords": ["channel", "focus", "growth", "one thing", "spread thin", "multichannel", "which channel"],
    },
    "do-charge-from-day-one": {
        "title": "Charge Real Money From Day One",
        "type": "DO",
        "summary": "Free users give you noise. Paying customers give you signal.",
        "keywords": ["pricing", "free", "freemium", "charge", "monetize", "revenue", "price", "how much to charge", "subscription"],
    },
    "do-embrace-the-grind": {
        "title": "Embrace the Grind",
        "type": "DO",
        "summary": "Success requires doing unglamorous work. Learn fast, adapt faster.",
        "keywords": ["grind", "hard work", "hustle", "learn", "skill", "mentorship", "effort"],
    },
    "do-consistency-beats-talent": {
        "title": "Consistency Beats Talent",
        "type": "DO",
        "summary": "Show up every day. The founders who win are the ones who don't stop.",
        "keywords": ["consistency", "daily", "routine", "habit", "discipline", "compound", "long game", "patience", "show up"],
    },
    "dont-give-up-too-early": {
        "title": "Don't Give Up Too Early",
        "type": "DONT",
        "summary": "Most founders quit right before it clicks. Give it 12-24 months minimum.",
        "keywords": ["give up", "quit", "too early", "patience", "persist", "almost quit", "how long", "when to quit idea"],
    },
    "dont-target-everyone": {
        "title": "Don't Try to Target Everyone",
        "type": "DONT",
        "summary": "A product for everyone is a product for no one. Go narrow, go deep.",
        "keywords": ["everyone", "too broad", "target market", "broad audience", "generic product", "who is this for", "niche down"],
    },
    "dont-overbuild-before-traction": {
        "title": "Don't Overbuild Before You Have Traction",
        "type": "DONT",
        "summary": "Building for 6 months without users is the most common founder mistake.",
        "keywords": ["overbuild", "too many features", "spent too long building", "scope creep", "feature creep", "gold plating", "perfectionism"],
    },
    "dont-ignore-distribution": {
        "title": "Don't Ignore Distribution",
        "type": "DONT",
        "summary": "If you build it, they won't come. Distribution is not optional.",
        "keywords": ["no traffic", "no users", "built it and nobody came", "forgot marketing", "distribution", "nobody knows", "invisible product"],
    },
    "dont-spread-across-channels": {
        "title": "Don't Spread Across Too Many Channels",
        "type": "DONT",
        "summary": "Doing 5 channels at 20% beats doing 1 channel at 100%. Wait — it doesn't.",
        "keywords": ["too many channels", "spread thin", "every channel", "unfocused marketing", "tried everything"],
    },
    "dont-underprice": {
        "title": "Don't Underprice Your Product",
        "type": "DONT",
        "summary": "Charging too little attracts bad customers and kills your margins. Compete on value, not price.",
        "keywords": ["too cheap", "underprice", "raise prices", "should charge more", "leaving money on table", "price too low", "race to bottom", "cheapest", "compete on price"],
    },
    "dont-add-features-to-fix-churn": {
        "title": "Don't Add Features to Fix Churn",
        "type": "DONT",
        "summary": "If people leave, it's not because you lack features. It's because the core isn't solving their problem.",
        "keywords": ["churn", "features won't fix", "adding features", "still churning", "why people leave", "cancel"],
    },
    "do-outsource-your-weaknesses": {
        "title": "Outsource Your Weaknesses Early",
        "type": "DO",
        "summary": "Don't learn everything — hire for what you're bad at.",
        "keywords": ["hire", "outsource", "team", "freelancer", "developer", "designer", "co-founder", "alone", "delegation"],
    },
    "do-compete-on-speed-not-features": {
        "title": "Compete on Speed, Not Features",
        "type": "DO",
        "summary": "You can't out-feature incumbents. But you can out-speed and out-care them.",
        "keywords": ["competition", "competitors", "differentiate", "moat", "crowded market", "red ocean", "positioning"],
    },
    "do-retention-over-acquisition": {
        "title": "Retention Beats Acquisition Every Time",
        "type": "DO",
        "summary": "A leaky bucket can't be filled. Fix churn before scaling growth.",
        "keywords": ["retention", "churn", "cancel", "keep customers", "support", "NPS", "lifetime value", "LTV"],
    },
    "do-plan-your-escape": {
        "title": "Plan Your Escape from Employment",
        "type": "DO",
        "summary": "Build the side project while employed, but have a clear exit number.",
        "keywords": ["quit job", "full-time", "side project", "employment", "bootstrap", "savings", "when to quit", "escape"],
    },
    "dont-raise-unless-you-must": {
        "title": "Don't Raise Money Unless You Absolutely Must",
        "type": "DONT",
        "summary": "Bootstrapping keeps you in control. VC money comes with strings.",
        "keywords": ["funding", "VC", "investors", "bootstrap", "raise money", "venture capital", "angel", "self-funded"],
    },
    "do-talk-to-customers": {
        "title": "Talk to Customers Obsessively",
        "type": "DO",
        "summary": "The answers aren't in your head. They're in customer conversations.",
        "keywords": ["customers", "feedback", "interviews", "talk to users", "customer development", "listening", "sales calls"],
    },
}


def load_extractions():
    with open(EXTRACTIONS_FILE) as f:
        return json.load(f)


def resolve_split(split_key, quote_text):
    """Resolve a SPLIT: category by matching quote text against keywords."""
    rules = SPLIT_KEYWORDS.get(split_key, {})
    quote_lower = quote_text.lower()

    for verdict_slug, keywords in rules.items():
        if keywords is None:
            continue  # default fallback
        for kw in keywords:
            if kw.lower() in quote_lower:
                return verdict_slug

    # Return the default (the one with keywords=None)
    for verdict_slug, keywords in rules.items():
        if keywords is None:
            return verdict_slug

    return None


# Mapping costly_mistakes to DON'T verdicts by keyword matching
MISTAKE_TO_VERDICT = {
    "dont-overbuild-before-traction": [
        "too many features", "overbuilt", "over-engineer", "spent too long", "months building",
        "year building", "feature creep", "scope creep", "too complex", "gold plat",
        "spent months", "spent years", "before anyone used", "before launching", "random features",
        "MVP", "too much time building", "building too long", "perfecti",
    ],
    "dont-ignore-distribution": [
        "no marketing", "didn't market", "nobody came", "no users", "zero traffic",
        "no customers", "couldn't get users", "failed to launch", "nothing happened",
        "no one signed up", "viral launch", "expected users",
    ],
    "dont-underprice": [
        "too cheap", "too low", "underpric", "should have charged", "wasn't charging enough",
        "raised price", "doubled price", "tripled", "lowering prices", "low price",
        "pricing too low", "charge more",
    ],
    "dont-target-everyone": [
        "too broad", "everyone", "general audience", "no niche", "unfocused",
        "trying to reach everyone", "no target", "no ICP",
    ],
    "dont-spread-across-channels": [
        "too many channels", "every channel", "spread thin", "tried everything",
        "Google ads", "cold email", "ads that were never profitable", "paid ads",
        "money on ads", "wasted on ads",
    ],
    "dont-add-features-to-fix-churn": [
        "features", "churn", "terrible paid conversion", "nobody's going to buy",
        "retention", "cancel", "users leaving",
    ],
}


def cluster_quotes(extractions):
    """Group all quotes by verdict slug. Also mines costly_mistakes for DON'T verdicts."""
    verdicts = {}
    unmapped = []

    for ext in extractions:
        founder = ext.get("founder_name", "Unknown")
        product = ext.get("product_name", "Unknown")
        revenue = ext.get("revenue", "Unknown")
        revenue_num = ext.get("revenue_numeric_monthly", 0)
        product_type = ext.get("product_type", "Unknown")
        niche = ext.get("niche", "Unknown")
        source_id = ext.get("_source_id", "")
        title = ext.get("_title", "")

        base_info = {
            "founder": founder, "product": product, "revenue": revenue,
            "revenue_numeric": revenue_num, "product_type": product_type,
            "niche": niche, "source_id": source_id, "title": title,
        }

        # --- Mine advice_quotes ---
        for quote in ext.get("advice_quotes", []):
            category = quote.get("category", "unknown")
            verdict_slug = CATEGORY_MAP.get(category)

            if not verdict_slug:
                unmapped.append(category)
                continue

            if verdict_slug.startswith("SPLIT:"):
                verdict_slug = resolve_split(verdict_slug, quote.get("quote", ""))
                if not verdict_slug:
                    unmapped.append(f"split-failed:{category}")
                    continue

            if verdict_slug not in verdicts:
                verdicts[verdict_slug] = []

            verdicts[verdict_slug].append({
                **base_info,
                "quote": quote.get("quote", ""),
                "category": category,
                "actionable": quote.get("actionable", False),
            })

        # --- Mine costly_mistakes for DON'T verdicts ---
        for mistake in ext.get("costly_mistakes", []):
            mistake_text = f"{mistake.get('mistake', '')} {mistake.get('lesson', '')}".lower()

            for verdict_slug, keywords in MISTAKE_TO_VERDICT.items():
                matched = False
                for kw in keywords:
                    if kw.lower() in mistake_text:
                        matched = True
                        break

                if matched:
                    if verdict_slug not in verdicts:
                        verdicts[verdict_slug] = []

                    # Format mistake as a quote
                    quote_text = f"{mistake.get('mistake', '')}. Lesson: {mistake.get('lesson', '')}"
                    if mistake.get("cost"):
                        quote_text = f"{mistake.get('mistake', '')} (cost: {mistake['cost']}). Lesson: {mistake.get('lesson', '')}"

                    verdicts[verdict_slug].append({
                        **base_info,
                        "quote": quote_text,
                        "category": "costly-mistake",
                        "actionable": True,
                    })
                    break  # One verdict per mistake

        # --- Mine pivot_moments for relevant verdicts ---
        for pivot in ext.get("pivot_moments", []):
            pivot_text = f"{pivot.get('before', '')} {pivot.get('after', '')} {pivot.get('trigger', '')}".lower()

            # Pivots often relate to overbuild or target-everyone
            if any(kw in pivot_text for kw in ["too broad", "wrong market", "wrong audience", "everyone"]):
                slug = "dont-target-everyone"
            elif any(kw in pivot_text for kw in ["too complex", "simpler", "stripped", "removed features"]):
                slug = "dont-overbuild-before-traction"
            else:
                continue

            if slug not in verdicts:
                verdicts[slug] = []

            quote_text = f"Pivoted from {pivot.get('before', '?')} to {pivot.get('after', '?')}. Why: {pivot.get('trigger', '?')}"
            if pivot.get("revenue_impact"):
                quote_text += f". Impact: {pivot['revenue_impact']}"

            verdicts[slug].append({
                **base_info,
                "quote": quote_text,
                "category": "pivot",
                "actionable": True,
            })

    if unmapped:
        from collections import Counter
        print(f"\nUnmapped categories: {Counter(unmapped).most_common()}")

    return verdicts


def revenue_stage(rev_num):
    """Classify revenue stage."""
    if rev_num == 0:
        return "Unknown"
    elif rev_num < 1000:
        return "$0-1K/mo"
    elif rev_num < 5000:
        return "$1K-5K/mo"
    elif rev_num < 10000:
        return "$5K-10K/mo"
    elif rev_num < 50000:
        return "$10K-50K/mo"
    elif rev_num < 100000:
        return "$50K-100K/mo"
    else:
        return "$100K+/mo"


def write_verdict_file(slug, quotes, meta):
    """Write a single verdict markdown file."""
    # Sort quotes by revenue (highest first) for credibility
    quotes.sort(key=lambda q: q["revenue_numeric"], reverse=True)

    # Deduplicate by founder (keep highest-quality quote per founder)
    seen_founders = set()
    unique_quotes = []
    for q in quotes:
        key = q["founder"]
        if key not in seen_founders:
            seen_founders.add(key)
            unique_quotes.append(q)

    # Group by revenue stage
    by_stage = {}
    for q in unique_quotes:
        stage = revenue_stage(q["revenue_numeric"])
        if stage not in by_stage:
            by_stage[stage] = []
        by_stage[stage].append(q)

    # Build markdown
    lines = []
    # Avoid "DONT: Don't X" double negation — DON'T titles already have "Don't"
    if meta['type'] == 'DONT':
        clean_title = meta['title'].replace("Don't ", "")
        lines.append(f"# DON'T: {clean_title}")
    else:
        lines.append(f"# DO: {meta['title']}")
    lines.append("")
    lines.append(f"> {meta['summary']}")
    lines.append("")
    lines.append(f"**{len(unique_quotes)} founders** weighed in on this. **{len(quotes)} total mentions** across {len(seen_founders)} interviews.")
    lines.append("")

    # Revenue stage breakdown
    stage_order = ["$100K+/mo", "$50K-100K/mo", "$10K-50K/mo", "$5K-10K/mo", "$1K-5K/mo", "$0-1K/mo", "Unknown"]
    for stage in stage_order:
        stage_quotes = by_stage.get(stage, [])
        if not stage_quotes:
            continue

        lines.append(f"## At {stage}")
        lines.append("")
        for q in stage_quotes[:8]:  # Max 8 per stage
            revenue_label = q["revenue"] if q["revenue"] != "Unknown" else "undisclosed"
            lines.append(f"**{q['founder']}** — {q['product']} ({q['product_type']}, {revenue_label})")
            lines.append(f"> \"{q['quote']}\"")
            lines.append("")

    # Stats footer
    product_types = {}
    for q in unique_quotes:
        pt = q["product_type"]
        product_types[pt] = product_types.get(pt, 0) + 1

    lines.append("---")
    lines.append("")
    lines.append("## Stats")
    lines.append(f"- **Total mentions:** {len(quotes)}")
    lines.append(f"- **Unique founders:** {len(unique_quotes)}")
    top_types = sorted(product_types.items(), key=lambda x: -x[1])[:5]
    lines.append(f"- **Top product types:** {', '.join(f'{t} ({c})' for t, c in top_types)}")
    lines.append("")

    filepath = os.path.join(VERDICTS_DIR, f"{slug}.md")
    with open(filepath, "w") as f:
        f.write("\n".join(lines))

    return len(unique_quotes), len(quotes)


# DO/DON'T pairs for cross-referencing
VERDICT_PAIRS = {
    "do-validate-before-building": "dont-overbuild-before-traction",
    "do-pick-a-painful-niche": "dont-target-everyone",
    "do-keep-product-simple": "dont-overbuild-before-traction",
    "do-launch-fast-and-ugly": "dont-overbuild-before-traction",
    "do-marketing-from-day-one": "dont-ignore-distribution",
    "do-focus-on-one-channel": "dont-spread-across-channels",
    "do-charge-from-day-one": "dont-underprice",
    "do-retention-over-acquisition": "dont-add-features-to-fix-churn",
    "do-plan-your-escape": "dont-raise-unless-you-must",
    "do-embrace-the-grind": "dont-give-up-too-early",
    "do-consistency-beats-talent": "dont-give-up-too-early",
}
# Build reverse pairs
VERDICT_PAIRS_REVERSE = {v: k for k, v in VERDICT_PAIRS.items()}


def build_index(verdicts):
    """Build index.json for routing queries to verdicts."""
    index = {"version": 1, "verdicts": []}

    for slug, meta in VERDICT_META.items():
        quotes = verdicts.get(slug, [])
        unique_founders = len(set(q["founder"] for q in quotes))

        # Find paired verdict
        pair = VERDICT_PAIRS.get(slug) or VERDICT_PAIRS_REVERSE.get(slug)

        entry = {
            "slug": slug,
            "title": meta["title"],
            "type": meta["type"],
            "summary": meta["summary"],
            "keywords": meta["keywords"],
            "mentions": len(quotes),
            "founders": unique_founders,
            "file": f"verdicts/{slug}.md",
        }
        if pair:
            entry["pair"] = pair

        index["verdicts"].append(entry)

    # Sort by mentions descending
    index["verdicts"].sort(key=lambda v: -v["mentions"])

    filepath = os.path.join(REFS_DIR, "index.json")
    with open(filepath, "w") as f:
        json.dump(index, f, indent=2)

    return index


def build_sources(extractions):
    """Build sources.json with video/founder metadata."""
    sources = []
    for ext in extractions:
        sources.append({
            "founder": ext.get("founder_name", "Unknown"),
            "product": ext.get("product_name", "Unknown"),
            "product_type": ext.get("product_type", "Unknown"),
            "revenue": ext.get("revenue", "Unknown"),
            "revenue_monthly": ext.get("revenue_numeric_monthly", 0),
            "niche": ext.get("niche", "Unknown"),
            "title": ext.get("_title", ""),
            "source_id": ext.get("_source_id", ""),
            "quotes_extracted": len(ext.get("advice_quotes", [])),
            "channels": [c.get("channel") for c in ext.get("channels", [])],
            "first_customer_method": ext.get("first_customer", {}).get("method", "Unknown"),
            "interview_quality": ext.get("interview_quality", "unknown"),
        })

    # Sort by revenue
    sources.sort(key=lambda s: -s["revenue_monthly"])

    filepath = os.path.join(REFS_DIR, "sources.json")
    with open(filepath, "w") as f:
        json.dump({"version": 1, "count": len(sources), "sources": sources}, f, indent=2)

    return sources


def main():
    print("Loading extractions...")
    extractions = load_extractions()
    print(f"Loaded {len(extractions)} founder interviews")

    print("\nClustering quotes into verdicts...")
    verdicts = cluster_quotes(extractions)

    print(f"\nWriting {len(VERDICT_META)} verdict files...")
    total_quotes = 0
    total_founders = 0
    for slug, meta in VERDICT_META.items():
        quotes = verdicts.get(slug, [])
        if not quotes:
            print(f"  ⚠ {slug}: 0 quotes (skipping)")
            continue
        founders, mentions = write_verdict_file(slug, quotes, meta)
        total_founders += founders
        total_quotes += mentions
        print(f"  ✓ {slug}: {founders} founders, {mentions} mentions")

    print(f"\nBuilding index.json...")
    index = build_index(verdicts)
    print(f"  {len(index['verdicts'])} verdicts indexed")

    print(f"\nBuilding sources.json...")
    sources = build_sources(extractions)
    print(f"  {len(sources)} founder sources")

    print(f"\n{'='*60}")
    print(f"Done!")
    print(f"  Verdict files: {VERDICTS_DIR}/")
    print(f"  Index: {REFS_DIR}/index.json")
    print(f"  Sources: {REFS_DIR}/sources.json")
    print(f"  Total: {total_quotes} quotes from {total_founders} founders across {len(VERDICT_META)} verdicts")


if __name__ == "__main__":
    main()
