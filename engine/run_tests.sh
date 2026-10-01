#!/usr/bin/env bash
# Everything here runs offline against no model weights, in a few seconds.
#   ./run_tests.sh
set -u
PY="${PY:-./.venv/bin/python}"
[ -x "$PY" ] || PY=python3
fail=0

echo "=============================================================="
echo " 1. false positives — 30 strings that must pass through intact"
echo "=============================================================="
"$PY" scripts/test_safety.py || fail=1

echo
echo "=============================================================="
echo " 2. rewriting — European Spanish into espanol neutro"
echo "=============================================================="
"$PY" scripts/neutro.py

echo "=============================================================="
echo " 3. JS port matches Python byte-for-byte"
echo "=============================================================="
if command -v node >/dev/null 2>&1; then
  "$PY" scripts/crosscheck.py || fail=1
else
  echo "SKIPPED (node not installed)"
fi

echo
if [ "$fail" -eq 0 ]; then echo "ALL PASS"; else echo "FAILURES ABOVE"; fi
exit $fail
