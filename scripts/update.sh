#!/bin/bash
# update.sh — One command to refresh the founder-advice skill
#
# Prerequisites:
#   - ANTHROPIC_API_KEY set in environment
#   - Python 3 with anthropic package installed
#   - NotebookLM CLI (notebooklm-py) for new transcripts
#
# Usage:
#   ./scripts/update.sh              # Extract + rebuild from existing transcripts
#   ./scripts/update.sh --full       # Pull new videos + transcripts + extract + rebuild
#
# Pipeline:
#   1. [--full only] Check for new Starter Story videos via yt-dlp
#   2. [--full only] Pull new transcripts via NotebookLM
#   3. Run extract-advice.py (resumable — skips already-extracted)
#   4. Run build-verdicts.py (rebuilds all verdict files)
#   5. Show diff summary

set -e
cd "$(dirname "$0")/.."

echo "=== founder-advice update ==="
echo ""

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

# Step 1-2: Full mode — check for new videos
if [ "$1" = "--full" ]; then
    echo "[1/4] Checking for new Starter Story videos..."

    # Pull latest video list
    yt-dlp --flat-playlist --print "%(id)s|%(title)s|%(view_count)s|%(duration)s" \
        "https://www.youtube.com/@starterstory/videos" \
        --playlist-end 200 > /tmp/starter-story-latest.txt 2>/dev/null || true

    CURRENT=$(ls data/transcripts-nlm/ 2>/dev/null | wc -l | tr -d ' ')
    LATEST=$(wc -l < /tmp/starter-story-latest.txt | tr -d ' ')
    echo "  Current transcripts: $CURRENT"
    echo "  Videos on channel: $LATEST"

    if [ "$LATEST" -gt "$CURRENT" ]; then
        NEW=$((LATEST - CURRENT))
        echo "  $NEW new videos found. Add them to NotebookLM and run:"
        echo "    notebooklm source fulltext <source_id>"
        echo "  Save transcripts to data/transcripts-nlm/"
        echo ""
        echo "  Then re-run: ./scripts/update.sh"
        exit 0
    else
        echo "  No new videos. Continuing with extraction..."
    fi
    echo ""
fi

# Step 3: Extract advice from transcripts
echo "[2/4] Extracting advice from transcripts..."
python3 scripts/extract-advice.py
echo ""

# Step 4: Build verdict files
echo "[3/4] Building verdict files..."
python3 scripts/build-verdicts.py
echo ""

# Step 5: Summary
echo "[4/4] Summary"
echo ""
VERDICTS=$(ls references/verdicts/*.md 2>/dev/null | wc -l | tr -d ' ')
QUOTES=$(python3 -c "import json; d=json.load(open('data/extractions.json')); print(sum(len(x.get('advice_quotes',[])) for x in d))")
FOUNDERS=$(python3 -c "import json; d=json.load(open('data/extractions.json')); print(len(d))")

echo "  Founders: $FOUNDERS"
echo "  Quotes: $QUOTES"
echo "  Verdicts: $VERDICTS"
echo ""

# Show git diff
CHANGED=$(git diff --stat references/ SKILL.md 2>/dev/null | tail -1)
if [ -n "$CHANGED" ]; then
    echo "  Changes: $CHANGED"
    echo ""
    echo "  To publish: git add -A && git commit -m 'update: refreshed verdicts' && git push"
else
    echo "  No changes to publish."
fi
