#!/usr/bin/env bash
# VL-10: walk BUILD_BRIEF.md Section 25 (Definition of Done) top to bottom against the current
# checkout. For the true "clean checkout" guarantee, run this from a fresh `git clone`.
# Usage: bash scripts/check_dod.sh
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0
pass() { echo "PASS  $1"; }
die()  { echo "FAIL  $1"; fail=1; }

echo "### Definition-of-Done check @ $(git rev-parse --short HEAD 2>/dev/null || echo '?')"

uv sync >/dev/null 2>&1 && pass "1 uv sync" || die "1 uv sync"
uv run ruff check . >/dev/null 2>&1 && pass "2 ruff check" || die "2 ruff check"
uv run ruff format --check . >/dev/null 2>&1 && pass "3 ruff format --check" || die "3 format"
uv run mypy src >/dev/null 2>&1 && pass "4 mypy src" || die "4 mypy"
uv run pytest -q >/dev/null 2>&1 && pass "5 pytest (coverage ratchet)" || die "5 pytest"
uv build >/dev/null 2>&1 && ls dist/*.whl >/dev/null 2>&1 && pass "6 uv build (wheel)" || die "6 build"

uv run collection-ci scan --mapping examples/mappings/clean.yaml --output-dir build/clean >/dev/null 2>&1
c=$?; n=$(python3 -c "import json;print(len(json.load(open('build/clean/findings.json'))))" 2>/dev/null)
[ "$c" = 0 ] && [ "$n" = 0 ] && pass "7 clean scan (exit 0, 0 findings)" || die "7 clean scan (exit=$c findings=$n)"

uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/dirty >/dev/null 2>&1
c=$?; ids=$(python3 -c "import json;print(sorted({f['rule']['id'] for f in json.load(open('build/dirty/findings.json'))}))" 2>/dev/null)
echo "$ids" | grep -q CORE001 && [ "$c" = 1 ] && pass "8 dirty scan (exit 1, labeled findings)" || die "8 dirty scan (exit=$c)"

out=$(uv run collection-ci benchmark --output-dir build/benchmark 2>&1); c=$?
echo "$out" | grep -q "meets target: yes" && [ "$c" = 0 ] && pass "9 benchmark (meets target)" || die "9 benchmark"

if grep -Eq 'src="http|href="http|@import|https?://[^"]*\.(js|css)' build/dirty/report.html; then
  die "10 HTML self-contained (external asset found)"; else pass "10 HTML report self-contained"; fi

python3 - <<'PY' && pass "11 SARIF structure valid" || die "11 SARIF"
import json
d=json.load(open('build/dirty/results.sarif'))
assert d['version']=='2.1.0'
assert d['$schema'].endswith('sarif-2.1.0.json')
assert d['runs'][0]['tool']['driver']['rules']
assert d['runs'][0]['results']
PY

if grep -rEq 'secrets\.[A-Za-z]' .github/workflows/; then die "12 workflows use secrets"; else pass "12 workflows secret-free"; fi
grep -q 'examples/mappings/clean.yaml' README.md && ! grep -q -- '--rules' README.md \
  && pass "13 README quick start matches CLI" || die "13 README quick start"
python3 -c "import json;m=json.load(open('build/dirty/run_manifest.json'));assert m['ai_providers_used'] is False and m['network_access_used'] is False" 2>/dev/null \
  && pass "14 no AI provider / no network (manifest)" || die "14 manifest offline flags"
[ -z "$(git status --porcelain examples/)" ] && pass "15 source data unmodified" || die "15 examples/ modified"
[ -f docs/FUTURE_SCOPE.md ] && grep -qi 'non-goal\|limitation' docs/PRD.md docs/FUTURE_SCOPE.md 2>/dev/null \
  && pass "16 limitations/non-goals documented" || die "16 limitations docs"
[ -f docs/PROGRESS.md ] && [ -f docs/THREAT_MODEL.md ] && pass "17 progress/threat docs present" || die "17 docs"

cp build/dirty/findings.json build/baseline.json
out=$(uv run collection-ci scan --mapping examples/mappings/dirty.yaml --output-dir build/rescan \
  --baseline build/baseline.json --only-new 2>&1); c=$?
echo "$out" | grep -q "0 new" && [ "$c" = 0 ] && pass "18 demo baseline/--only-new (0 new, exit 0)" || die "18 demo rescan (exit=$c)"

echo "-----"
[ "$fail" = 0 ] && echo "DoD: ALL CHECKS PASSED" || echo "DoD: FAILURES PRESENT"
exit $fail
