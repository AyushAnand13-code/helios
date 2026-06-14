#!/usr/bin/env bash
# Regenerate readable PDF versions of every Markdown file in the repo.
#
# Source markdown lives under  markdown/   (mirrors the original repo layout),
#   plus root-level CLAUDE.md / README.md   (kept at root for tooling + GitHub).
# Output PDFs go to            pdf/         (same relative path, minus markdown/).
# Source markdown is NEVER modified or deleted.
#
# Requirements (already present on this machine):
#   - pandoc            (Markdown -> styled HTML)
#   - Google Chrome     (headless HTML -> PDF; Edge works too)
#
# Usage:  bash scripts/md_to_pdf.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
[ -f "$CHROME" ] || CHROME="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
CSS="scripts/pdf-style.css"
TMP=".pdfwork"; mkdir -p "$TMP"

ok=0; fail=0; failed=""
while IFS= read -r f; do
  rel="${f#markdown/}"             # strip markdown/ prefix; root files keep their name
  base="$(basename "$rel" .md)"
  outdir="pdf/$(dirname "$rel")"; mkdir -p "$outdir"
  html="$TMP/tmp.html"
  pandoc "$f" -f gfm -t html5 --standalone --embed-resources \
    --metadata title="$base" -c "$CSS" -o "$html" 2>/dev/null
  [ -s "$html" ] || { fail=$((fail+1)); failed="$failed\n  $rel (pandoc)"; continue; }
  outpdf="$outdir/$base.pdf"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$(cygpath -m "$ROOT/$outpdf")" \
    "file:///$(cygpath -m "$ROOT/$html")" >/dev/null 2>&1
  [ -s "$outpdf" ] && ok=$((ok+1)) || { fail=$((fail+1)); failed="$failed\n  $rel (chrome)"; }
done < <(find markdown -name '*.md' -not -path '*/.git/*'; \
         find . -maxdepth 1 -name '*.md' -printf '%P\n')   # + root CLAUDE.md / README.md

rm -rf "$TMP"
echo "PDF regen complete  ->  OK: $ok  FAIL: $fail"
[ -n "$failed" ] && echo -e "Failures:$failed"
exit 0
