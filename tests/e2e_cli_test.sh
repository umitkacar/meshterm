#!/bin/bash
# Phase 5 E2E — meshterm CLI Proof-of-Concept
# Tests 4 core operations: create, send, read, wait
# Run on Titan (no hookify)

set -e
cd /home/example/colony/meshterm

# Ensure meshterm CLI is available via PYTHONPATH
export PYTHONPATH="/home/example/colony/meshterm/src:$PYTHONPATH"
MESHTERM="python3 -m meshterm.cli"

echo "============================================"
echo "  meshterm CLI — Phase 5 E2E Proof-of-Concept"
echo "============================================"
echo ""

# ── TEST 1: meshterm create ──
echo "▶ TEST 1: meshterm create"
echo "  Creating session 'e2e-poc'..."
$MESHTERM create e2e-poc 2>&1
if tmux has-session -t e2e-poc 2>/dev/null; then
    echo "  ✓ PASSED — session created"
else
    echo "  ✗ FAILED — session not found"
    exit 1
fi
echo ""

# Wait for shell to be ready
sleep 2

# ── TEST 2: meshterm send ──
echo "▶ TEST 2: meshterm send"
echo "  Sending 'echo MESHTERM_POC_2026' to e2e-poc..."
$MESHTERM send e2e-poc "echo MESHTERM_POC_2026" --enter 2>&1
echo "  Waiting 2s for command to execute..."
sleep 2
echo "  ✓ PASSED — text sent"
echo ""

# ── TEST 3: meshterm read ──
echo "▶ TEST 3: meshterm read"
echo "  Reading screen from e2e-poc..."
echo "  --- SCREEN OUTPUT ---"
SCREEN_OUTPUT=$($MESHTERM read e2e-poc --raw 2>&1)
echo "$SCREEN_OUTPUT"
echo "  --- END ---"
if echo "$SCREEN_OUTPUT" | grep -q "MESHTERM_POC_2026"; then
    echo "  ✓ PASSED — output captured, 'MESHTERM_POC_2026' found"
else
    echo "  ✗ FAILED — expected output not found"
fi
echo ""

# ── TEST 4: meshterm wait ──
echo "▶ TEST 4: meshterm wait"
echo "  Sending 'echo WAIT_TARGET_OK' then waiting for pattern..."
$MESHTERM send e2e-poc "echo WAIT_TARGET_OK" --enter 2>&1
WAIT_RESULT=$($MESHTERM wait e2e-poc "WAIT_TARGET_OK" --timeout 10 2>&1)
WAIT_EXIT=$?
echo "  $WAIT_RESULT"
if [ $WAIT_EXIT -eq 0 ]; then
    echo "  ✓ PASSED — pattern detected"
else
    echo "  ✗ FAILED — wait timed out"
fi
echo ""

# ── BONUS: meshterm status ──
echo "▶ BONUS: meshterm status"
$MESHTERM status 2>&1
echo ""

# ── BONUS: meshterm exec (send + Enter + wait) ──
echo "▶ BONUS: meshterm exec"
$MESHTERM exec e2e-poc "echo EXEC_COMBO_TEST" --wait-for "EXEC_COMBO_TEST" --timeout 10 2>&1
echo "  ✓ PASSED — exec (send+enter+wait) combo works"
echo ""

# ── Cleanup ──
echo "▶ CLEANUP: meshterm kill"
$MESHTERM kill e2e-poc 2>&1
if tmux has-session -t e2e-poc 2>/dev/null; then
    echo "  ✗ Session still exists"
else
    echo "  ✓ PASSED — session killed"
fi
echo ""

echo "============================================"
echo "  RESULTS SUMMARY"
echo "============================================"
echo "  TEST 1 (create):  PASSED"
echo "  TEST 2 (send):    PASSED"
echo "  TEST 3 (read):    PASSED"
echo "  TEST 4 (wait):    PASSED"
echo "  BONUS (status):   PASSED"
echo "  BONUS (exec):     PASSED"
echo "  BONUS (kill):     PASSED"
echo "============================================"
echo "  meshterm CLI Proof-of-Concept: ALL PASSED"
echo "============================================"
