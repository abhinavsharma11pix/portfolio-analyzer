#!/bin/bash
# =============================================================
# PortfolioAI — Complete Project Audit
# Run from project root: bash audit_project.sh
# Produces: audit_report.txt
# =============================================================

set -e
ROOT="$(pwd)"
REPORT="audit_report.txt"

echo "=============================================="  > "$REPORT"
echo "  PORTFOLIOAI PROJECT AUDIT"                     >> "$REPORT"
echo "  Generated: $(date)"                            >> "$REPORT"
echo "=============================================="  >> "$REPORT"

# ── 1. FOLDER STRUCTURE (excluding heavy dirs) ──────────────
echo ""                                                >> "$REPORT"
echo "── 1. PROJECT STRUCTURE ─────────────────────"   >> "$REPORT"
find . \
  -path ./node_modules -prune -o \
  -path ./frontend/node_modules -prune -o \
  -path ./backend/venv311 -prune -o \
  -path ./.git -prune -o \
  -path ./frontend/dist -prune -o \
  -path '*__pycache__*' -prune -o \
  -type f -print | sort >> "$REPORT"

# ── 2. FILE COUNTS BY EXTENSION ──────────────────────────────
echo ""                                                >> "$REPORT"
echo "── 2. FILE COUNTS BY TYPE ───────────────────"   >> "$REPORT"
find . \
  -path ./node_modules -prune -o \
  -path ./frontend/node_modules -prune -o \
  -path ./backend/venv311 -prune -o \
  -path ./.git -prune -o \
  -path '*__pycache__*' -prune -o \
  -type f -name "*.*" -print \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn >> "$REPORT"

# ── 3. LARGEST FILES (top 20, excluding deps) ────────────────
echo ""                                                >> "$REPORT"
echo "── 3. TOP 20 LARGEST FILES ──────────────────"   >> "$REPORT"
find . \
  -path ./node_modules -prune -o \
  -path ./frontend/node_modules -prune -o \
  -path ./backend/venv311 -prune -o \
  -path ./.git -prune -o \
  -type f -print0 \
  | xargs -0 du -h 2>/dev/null | sort -rh | head -20 >> "$REPORT"

# ── 4. DIRECTORY SIZES ────────────────────────────────────────
echo ""                                                >> "$REPORT"
echo "── 4. TOP-LEVEL DIRECTORY SIZES ─────────────"   >> "$REPORT"
du -sh ./* 2>/dev/null | sort -rh >> "$REPORT"
echo "" >> "$REPORT"
echo "Backend subdirs:" >> "$REPORT"
du -sh ./backend/*/ 2>/dev/null | sort -rh >> "$REPORT"
echo "" >> "$REPORT"
echo "Frontend subdirs:" >> "$REPORT"
du -sh ./frontend/*/ 2>/dev/null | sort -rh >> "$REPORT"

# ── 5. DUPLICATE FILES (by content hash) ──────────────────────
echo ""                                                >> "$REPORT"
echo "── 5. DUPLICATE FILES (same content) ────────"   >> "$REPORT"
find . \
  -path ./node_modules -prune -o \
  -path ./frontend/node_modules -prune -o \
  -path ./backend/venv311 -prune -o \
  -path ./.git -prune -o \
  -path '*__pycache__*' -prune -o \
  -type f -print0 \
  | xargs -0 md5 -r 2>/dev/null \
  | sort \
  | awk '{print $1}' | uniq -d > /tmp/dup_hashes.txt

if [ -s /tmp/dup_hashes.txt ]; then
  while read -r hash; do
    echo "Hash $hash:" >> "$REPORT"
    find . \
      -path ./node_modules -prune -o \
      -path ./frontend/node_modules -prune -o \
      -path ./backend/venv311 -prune -o \
      -type f -print0 \
      | xargs -0 md5 -r 2>/dev/null | grep "^$hash" >> "$REPORT"
  done < /tmp/dup_hashes.txt
else
  echo "No exact duplicate files found." >> "$REPORT"
fi

# ── 6. PYTHON: UNUSED CODE (vulture) ──────────────────────────
echo ""                                                >> "$REPORT"
echo "── 6. PYTHON UNUSED CODE (vulture) ──────────"   >> "$REPORT"
if [ -d "backend/venv311" ]; then
  source backend/venv311/bin/activate
  if ! command -v vulture &> /dev/null; then
    pip install vulture --quiet
  fi
  vulture backend/app --min-confidence 80 >> "$REPORT" 2>&1 || true
  deactivate
else
  echo "venv311 not found — skipping" >> "$REPORT"
fi

# ── 7. FRONTEND: UNUSED NPM PACKAGES (depcheck) ───────────────
echo ""                                                >> "$REPORT"
echo "── 7. UNUSED NPM PACKAGES (depcheck) ────────"   >> "$REPORT"
if [ -d "frontend" ]; then
  cd frontend
  npx depcheck --json 2>/dev/null \
    | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print('Unused dependencies:', d.get('dependencies', []))
    print('Unused devDependencies:', d.get('devDependencies', []))
    print('Missing dependencies:', list(d.get('missing', {}).keys()))
except Exception as e:
    print('depcheck failed:', e)
" >> "../$REPORT" 2>&1 || echo "depcheck failed — run 'npx depcheck' manually" >> "../$REPORT"
  cd ..
else
  echo "frontend/ not found" >> "$REPORT"
fi

# ── 8. ORPHANED PAGES (not imported in App.tsx) ───────────────
echo ""                                                >> "$REPORT"
echo "── 8. PAGES NOT REFERENCED IN App.tsx ───────"   >> "$REPORT"
if [ -f "frontend/src/App.tsx" ]; then
  for f in frontend/src/pages/*.tsx; do
    name=$(basename "$f" .tsx)
    if ! grep -q "$name" frontend/src/App.tsx; then
      echo "⚠ Possibly unused page: $f" >> "$REPORT"
    fi
  done
else
  echo "App.tsx not found" >> "$REPORT"
fi

# ── 9. ORPHANED COMPONENTS (zero imports anywhere) ────────────
echo ""                                                >> "$REPORT"
echo "── 9. COMPONENTS WITH ZERO IMPORTS ──────────"   >> "$REPORT"
if [ -d "frontend/src/components" ]; then
  for f in frontend/src/components/*.tsx; do
    name=$(basename "$f" .tsx)
    count=$(grep -rl "$name" frontend/src --include="*.tsx" --include="*.ts" | grep -v "$f" | wc -l | tr -d ' ')
    if [ "$count" -eq 0 ]; then
      echo "⚠ Possibly unused component: $f" >> "$REPORT"
    fi
  done
else
  echo "components/ not found" >> "$REPORT"
fi

# ── 10. BACKEND ROUTES NOT REGISTERED IN main.py ──────────────
echo ""                                                >> "$REPORT"
echo "── 10. ROUTE FILES NOT REGISTERED IN main.py ─" >> "$REPORT"
if [ -f "backend/app/main.py" ]; then
  for f in backend/app/api/routes/*.py; do
    name=$(basename "$f" .py)
    if [ "$name" != "__init__" ] && ! grep -q "routes.$name\|routes import.*$name\|$name import" backend/app/main.py; then
      echo "⚠ Possibly unregistered route: $f" >> "$REPORT"
    fi
  done
else
  echo "main.py not found" >> "$REPORT"
fi

# ── 11. GIT-TRACKED LARGE FILES (GitHub 100MB limit) ──────────
echo ""                                                >> "$REPORT"
echo "── 11. GIT-TRACKED FILES >5MB ───────────────"   >> "$REPORT"
if [ -d ".git" ]; then
  git ls-files -z | xargs -0 du -h 2>/dev/null | sort -rh | awk '$1 ~ /M|G/ {print}' | head -20 >> "$REPORT"
else
  echo "Not a git repo" >> "$REPORT"
fi

# ── 12. CHECK .gitignore COVERAGE ─────────────────────────────
echo ""                                                >> "$REPORT"
echo "── 12. .gitignore CHECK ─────────────────────"   >> "$REPORT"
for dir in "backend/venv311" "frontend/node_modules" "frontend/dist" "backend/__pycache__" "backend/portfolio.db"; do
  if [ -e "$dir" ]; then
    if git check-ignore -q "$dir" 2>/dev/null; then
      echo "✓ $dir is gitignored" >> "$REPORT"
    else
      echo "⚠ $dir EXISTS but is NOT gitignored — should be added!" >> "$REPORT"
    fi
  fi
done

# ── DONE ───────────────────────────────────────────────────────
echo ""                                                >> "$REPORT"
echo "=============================================="  >> "$REPORT"
echo "  AUDIT COMPLETE — see $REPORT"                  >> "$REPORT"
echo "=============================================="  >> "$REPORT"

echo ""
echo "✅ Audit complete. Report saved to: $REPORT"
echo ""
echo "Quick summary:"
echo "--------------"
grep -A2 "TOP-LEVEL DIRECTORY SIZES" "$REPORT" | tail -n +2 | head -5
echo ""
echo "Run: cat $REPORT   to see the full report"
