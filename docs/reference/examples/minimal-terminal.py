#!/usr/bin/env python3
"""
Minimal Terminal Emulator — 35 lines of Python
================================================
A working terminal emulator that connects to a shell via PTY.
No colors, no escape code parsing, no GPU — just raw I/O.

Works on: Linux, macOS
Requires: Python 3.6+

Usage:
    python3 minimal-terminal.py

Press Ctrl+D to exit.
"""

import os
import pty
import select
import sys
import termios
import tty

def main():
    # Save original terminal settings (to restore on exit)
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Create PTY pair and fork a child process
        master_fd, slave_fd = pty.openpty()
        pid = os.fork()

        if pid == 0:
            # === CHILD PROCESS: Become the shell ===
            os.close(master_fd)      # Child doesn't need master
            os.setsid()              # Create new session
            os.dup2(slave_fd, 0)     # stdin  = slave
            os.dup2(slave_fd, 1)     # stdout = slave
            os.dup2(slave_fd, 2)     # stderr = slave
            if slave_fd > 2:
                os.close(slave_fd)
            # Replace this process with a shell
            shell = os.environ.get("SHELL", "/bin/bash")
            os.execvp(shell, [shell])
        else:
            # === PARENT PROCESS: Be the terminal ===
            os.close(slave_fd)       # Parent doesn't need slave
            tty.setraw(sys.stdin)    # Put our terminal in raw mode

            while True:
                # Wait for data from either master PTY or stdin
                ready, _, _ = select.select([master_fd, sys.stdin], [], [], 0.1)

                if master_fd in ready:
                    # Shell produced output → display it
                    try:
                        data = os.read(master_fd, 4096)
                    except OSError:
                        break  # Shell exited
                    if not data:
                        break
                    sys.stdout.buffer.write(data)
                    sys.stdout.flush()

                if sys.stdin in ready:
                    # User typed something → send to shell
                    data = os.read(sys.stdin.fileno(), 4096)
                    if not data:
                        break
                    os.write(master_fd, data)

            # Clean up
            os.close(master_fd)
            os.waitpid(pid, 0)

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    main()
