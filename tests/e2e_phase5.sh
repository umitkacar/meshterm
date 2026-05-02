#!/bin/bash
# Phase 5 E2E Test — meshterm + Claude Code interaction
# Run on Titan only (no hookify)

SESSION="claude-e2e"

echo "=== Phase 5 E2E Test ==="
echo "Step 1: tmux session check"
tmux has-session -t $SESSION 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: tmux session $SESSION not found"
    exit 1
fi
echo "Session $SESSION exists: OK"

echo ""
echo "Step 2: Waiting 15 seconds for Claude Code to load..."
sleep 15

echo "Step 3: Capturing screen (raw tmux)..."
SCREEN=$(tmux capture-pane -t $SESSION -p)
echo "--- SCREEN (first 30 lines) ---"
echo "$SCREEN" | head -30
echo "--- END ---"

# Check Claude Code state
if echo "$SCREEN" | grep -qE '❯|claude>|Tips|help'; then
    echo "CHECKPOINT: Claude Code READY (prompt detected)"
    CLAUDE_READY=1
elif echo "$SCREEN" | grep -qE 'trust|Trust|Yes'; then
    echo "CHECKPOINT: Claude Code asking trust - sending Enter..."
    tmux send-keys -t $SESSION Enter
    sleep 10
    CLAUDE_READY=1
else
    echo "CHECKPOINT: Claude Code state unknown"
    CLAUDE_READY=0
fi

echo ""
echo "Step 4: meshterm interaction test..."
cd /home/example/colony/meshterm
python3 -c "
import sys
sys.path.insert(0, 'src')
from meshterm.libtmux_session import LibtmuxSession, LibtmuxApp

app = LibtmuxApp()
sessions = app.list_sessions()
print(f'Total tmux panes: {len(sessions)}')
for s in sessions:
    print(f'  - pane={s.pane_id} cmd={s.current_command} cwd={s.cwd}')

# Find claude-e2e by session name
session = app.get_session_by_name('claude-e2e')
if session:
    print(f'Found session: pane={session.pane_id}')

    # Read screen via meshterm (use read_screen_text for string)
    screen_text = session.read_screen_text()
    print(f'Screen length: {len(screen_text)} chars')
    print(f'First 300 chars:')
    print(screen_text[:300])

    # Also test ScreenContents API
    sc = session.read_screen()
    print(f'ScreenContents: {sc.number_of_lines} lines, cursor=({sc.cursor_x},{sc.cursor_y})')

    # Send a simple echo command to Claude Code
    session.send_text('echo MESHTERM_E2E_TEST_OK')
    session.send_key('Enter')

    import time
    time.sleep(8)

    # Read screen after sending
    screen2 = session.read_screen_text()
    if 'MESHTERM_E2E_TEST_OK' in screen2:
        print('')
        print('==========================')
        print('TEXT INJECTION: PASSED!')
        print('SCREEN READING: PASSED!')
        print('==========================')
    else:
        print('TEXT INJECTION: sent but not yet visible')
        print(f'Screen after send: {screen2[:300]}')

    # Test metadata
    meta = session.metadata
    print(f'Metadata: {meta}')
    print('')
    print('E2E MESHTERM INTERACTION TEST COMPLETE')
else:
    print('ERROR: claude-e2e session not found via meshterm')
    print('Available tmux sessions:')
    import subprocess
    result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
    print(result.stdout)
"

echo ""
echo "=== Phase 5 E2E Test Done ==="
