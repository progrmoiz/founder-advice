#!/usr/bin/env python3
"""
Extract structured founder advice from Starter Story interview transcripts.
Uses Gemini Flash for fast, cheap extraction.

Outputs one JSON file per transcript in data/extractions/
Also builds a combined extractions.json with all results.

Resumable — skips already-processed transcripts.
"""
import json
import os
import sys
import time
import re
import glob

try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    os.system(f"{sys.executable} -m pip install anthropic -q")
    import anthropic

# --- Config ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "data", "transcripts-nlm")
EXTRACTIONS_DIR = os.path.join(BASE_DIR, "data", "extractions")
COMBINED_FILE = os.path.join(BASE_DIR, "data", "extractions.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "data", "extraction-progress.json")

os.makedirs(EXTRACTIONS_DIR, exist_ok=True)

# Rate limiting
DELAY_BETWEEN_REQUESTS = 1.0  # seconds between requests
BATCH_SIZE = 20
BATCH_COOLDOWN = 5

# --- Anthropic setup ---
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: ANTHROPIC_API_KEY not set")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-20250514"

# --- Extraction prompt ---
EXTRACTION_PROMPT = """You are analyzing a Starter Story YouTube interview transcript. Extract structured founder advice data.

The transcript is an interview between Pat Walls (host) and a founder discussing their business.

Extract the following. Be thorough — pull EVERY piece of advice, every revenue number, every specific tactic mentioned. Use exact quotes where possible (1-3 sentences max per quote).

Return ONLY valid JSON with this schema (no markdown, no code blocks, just raw JSON):

{
  "founder_name": "string — the founder's name",
  "product_name": "string — the product/company name",
  "product_type": "string — e.g., 'SaaS', 'mobile app', 'marketplace', 'agency', 'e-commerce', 'content site'",
  "revenue": "string — current MRR or revenue figure mentioned (e.g., '$40K/mo', '$1.5M/yr')",
  "revenue_numeric_monthly": 0,
  "niche": "string — the market/vertical",
  "founder_profile": {
    "technical": true,
    "solo": true,
    "bootstrapped": true,
    "previous_failures": 0,
    "location": "string or null"
  },
  "revenue_timeline": [
    {"period": "string — e.g., 'months 1-6'", "revenue": "string", "what_changed": "string"}
  ],
  "first_customer": {
    "method": "string — specific channel/tactic",
    "story": "string — 1-2 sentence description",
    "time_to_first_sale": "string or null"
  },
  "channels": [
    {
      "channel": "string — e.g., 'TikTok organic', 'SEO', 'cold email', 'Reddit'",
      "stage": "string — revenue range when used",
      "result": "string — what happened",
      "still_using": true
    }
  ],
  "pricing": [
    {
      "price": "string — e.g., '$29/mo', '$49 one-time'",
      "model": "string — 'subscription', 'one-time', 'freemium', 'usage-based'",
      "stage": "string — when this pricing was used",
      "change_result": "string or null — what happened when they changed"
    }
  ],
  "pivot_moments": [
    {
      "before": "string — what they were doing",
      "after": "string — what they switched to",
      "trigger": "string — why they pivoted",
      "revenue_impact": "string or null"
    }
  ],
  "costly_mistakes": [
    {
      "mistake": "string — what went wrong",
      "cost": "string — time or money lost",
      "lesson": "string — what they learned"
    }
  ],
  "advice_quotes": [
    {
      "quote": "string — verbatim or near-verbatim 1-3 sentences from the founder",
      "category": "string — e.g., 'validation', 'pricing', 'marketing', 'hiring', 'mindset', 'product', 'growth', 'retention', 'monetization', 'launch', 'quitting-job', 'competition', 'outsourcing', 'iteration', 'niche-selection'",
      "revenue_context": "string — founder's revenue when giving this advice",
      "actionable": true
    }
  ],
  "tools_mentioned": ["string — specific tools, platforms, services mentioned"],
  "key_metric": "string or null — the most important metric they track (e.g., 'LTV', 'CAC', 'conversion rate')",
  "interview_quality": "high|medium|low — how much actionable advice was in this interview"
}

RULES:
- If information is not mentioned, use null or empty arrays. Don't invent data.
- Revenue numbers must be EXACT as stated in the interview. Don't estimate.
- Quotes should be as close to verbatim as possible.
- Extract ALL advice quotes — aim for 5-15 per interview.
- Category tags should be from the list above, but you can add new ones if needed.
- Be specific. "Use content marketing" is too vague. "Post TikTok videos with entertainment-first format and 2-second CTA at the end" is specific.
- For revenue_numeric_monthly: convert to monthly USD integer. $40K/mo = 40000. $1.5M/yr = 125000. Unknown = 0.

TRANSCRIPT:
"""


def extract_from_transcript(filepath):
    """Extract structured data from a single transcript."""
    with open(filepath, "r") as f:
        content = f.read()

    # Get title from first line
    title = content.split("\n")[0].replace("# ", "")

    # Get source ID from second line
    source_id_line = content.split("\n")[1] if len(content.split("\n")) > 1 else ""
    source_id = source_id_line.replace("# Source ID: ", "").strip()

    # Skip very short transcripts (likely processing errors)
    if len(content) < 500:
        return None, "too_short"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT + content,
            }],
        )

        text = response.content[0].text.strip()

        # Clean up common JSON issues
        # Remove markdown code blocks if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        data = json.loads(text)

        # Add metadata
        data["_source_id"] = source_id
        data["_title"] = title
        data["_transcript_file"] = os.path.basename(filepath)

        return data, None

    except json.JSONDecodeError as e:
        return None, f"json_parse_error: {str(e)[:100]}"
    except Exception as e:
        return None, f"api_error: {str(e)[:200]}"


def save_progress(success, failed, skipped, total):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "success": success,
            "failed": len(failed),
            "skipped": skipped,
            "total": total,
            "failed_files": failed,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f, indent=2)


def main():
    # Get all transcript files
    files = sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.txt")))
    print(f"Found {len(files)} transcripts")

    success = 0
    failed = []
    skipped = 0
    batch_count = 0

    for i, filepath in enumerate(files):
        basename = os.path.basename(filepath).replace(".txt", "")
        out_path = os.path.join(EXTRACTIONS_DIR, f"{basename}.json")

        # Skip already processed
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100:
            skipped += 1
            continue

        # Batch cooldown
        fetched = success + len(failed)
        if fetched > 0 and fetched % BATCH_SIZE == 0:
            batch_count += 1
            print(f"\n--- Batch {batch_count} done ({fetched} processed). Cooling {BATCH_COOLDOWN}s ---\n")
            time.sleep(BATCH_COOLDOWN)

        # Extract
        title_line = open(filepath).readline().replace("# ", "").strip()[:60]
        print(f"[{skipped + success + 1}/{len(files)}] Processing: {title_line}...")

        data, error = extract_from_transcript(filepath)

        if data:
            with open(out_path, "w") as f:
                json.dump(data, f, indent=2)
            success += 1
            quotes = len(data.get("advice_quotes", []))
            revenue = data.get("revenue", "unknown")
            print(f"  ✓ {data.get('founder_name', '?')} | {revenue} | {quotes} quotes extracted")
        else:
            failed.append({"file": basename, "error": error})
            print(f"  ✗ FAILED: {error}")

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Save progress every 10
        if (success + len(failed)) % 10 == 0:
            save_progress(success, failed, skipped, len(files))

    # --- Build combined file ---
    print(f"\nBuilding combined extractions.json...")
    all_extractions = []
    for f in sorted(glob.glob(os.path.join(EXTRACTIONS_DIR, "*.json"))):
        with open(f) as fh:
            all_extractions.append(json.load(fh))

    with open(COMBINED_FILE, "w") as f:
        json.dump(all_extractions, f, indent=2)

    # --- Summary ---
    save_progress(success, failed, skipped, len(files))
    print(f"\n{'='*60}")
    print(f"Done! Extracted: {success} | Already had: {skipped} | Failed: {len(failed)}")
    print(f"Total: {skipped + success}/{len(files)}")
    print(f"Combined file: {COMBINED_FILE}")

    if failed:
        print(f"\nFailed files:")
        for f in failed[:10]:
            print(f"  - {f['file']}: {f['error']}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")


if __name__ == "__main__":
    main()
