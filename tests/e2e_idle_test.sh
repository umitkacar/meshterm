#!/bin/bash
# Phase 5 E2E — Idle Detection + Monitor Test
# Run on Titan

set -e
cd /home/example/colony/meshterm
export PYTHONPATH="/home/example/colony/meshterm/src:$PYTHONPATH"
MESHTERM="python3 -m meshterm.cli"

echo "============================================"
echo "  meshterm Idle Detection E2E Test"
echo "============================================"
echo ""

# ── TEST 1: Status with idle detection ──
echo ">>> TEST 1: meshterm status (with idle check — takes ~3s)"
$MESHTERM status 2>&1
echo ""

# ── TEST 2: Create sessions, one idle, one busy ──
echo ">>> TEST 2: Create idle + busy sessions"
$MESHTERM create idle-test 2>&1
sleep 2

# Send a long-running command to make one BUSY
$MESHTERM create busy-test --command "sleep 60" 2>&1
sleep 2

echo "  Checking status (idle-test should be IDLE, busy-test should be BUSY)..."
$MESHTERM status 2>&1
echo ""

# ── TEST 3: Monitor for 15 seconds with short threshold ──
echo ">>> TEST 3: Monitor with 10s threshold (watching for trigger)"
timeout 20 $MESHTERM monitor --interval 2 --threshold 10 --log /tmp/meshterm_idle_test.log 2>&1 || true
echo ""

# Check log
if [ -f /tmp/meshterm_idle_test.log ]; then
    echo "  Idle log:"
    cat /tmp/meshterm_idle_test.log
    echo "  PASSED — trigger logged"
else
    echo "  No trigger logged (sessions may still be busy)"
fi
echo ""

# ── TEST 4: Python API test ──
echo ">>> TEST 4: Python API idle detection"
python3 -c "
import sys
sys.path.insert(0, 'src')
from meshterm.libtmux_session import LibtmuxApp
from meshterm.idle_monitor import IdleMonitor, IdleConfig, SessionState

app = LibtmuxApp()
config = IdleConfig(poll_interval=1.0, min_idle_polls=2)
monitor = IdleMonitor(app, config=config)

# Poll 3 times
import time
for i in range(3):
    statuses = monitor.poll_once()
    time.sleep(1.0)

print(f'Sessions tracked: {len(statuses)}')
idle_count = sum(1 for s in statuses if s.state == SessionState.IDLE)
busy_count = sum(1 for s in statuses if s.state == SessionState.BUSY)
print(f'  IDLE: {idle_count}')
print(f'  BUSY: {busy_count}')
print(f'  All idle: {monitor.is_all_idle()}')
print(f'  All idle duration: {monitor.all_idle_duration():.1f}s')

for s in statuses:
    print(f'  {s.pane_id}: {s.state.value} cmd={s.command} idle={s.idle_seconds:.0f}s preview={s.screen_preview[:60]}')

# Callback test
triggered = []
monitor.on_session_idle(lambda s: triggered.append(s.pane_id))
monitor.poll_once()
print(f'  Callbacks fired for: {len(triggered)} sessions')
print('API TEST: PASSED')
" 2>&1
echo ""

# ── Cleanup ──
echo ">>> CLEANUP"
$MESHTERM kill idle-test 2>&1 || true
$MESHTERM kill busy-test 2>&1 || true
echo ""

echo "============================================"
echo "  Idle Detection E2E: COMPLETE"
echo "============================================"
