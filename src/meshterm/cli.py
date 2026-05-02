"""meshterm CLI — terminal control from command line.

Usage:
    meshterm status                  # list all sessions with IDLE/BUSY state
    meshterm send SESSION TEXT       # send text to session
    meshterm read SESSION            # read screen content
    meshterm key SESSION KEY         # send special key (Enter, Escape, C-c)
    meshterm wait SESSION PATTERN    # wait for pattern on screen
    meshterm create NAME             # create new session
    meshterm kill SESSION            # kill session
    meshterm monitor                 # continuous idle monitoring + cron trigger
    meshterm server start            # start custom PTY server (experimental)

Backend selection:
    --backend=libtmux   (default) Direct tmux control via libtmux
    --backend=custom    Experimental PTY server via Unix socket
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("meshterm CLI requires click: pip install meshterm[cli]", file=sys.stderr)
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


# ── Backend factory ──

def get_backend(backend: str) -> "LibtmuxApp":
    """Return the appropriate backend based on selection.

    Args:
        backend: Backend identifier ("libtmux" or "custom").

    Returns:
        Instantiated backend application. Currently only ``LibtmuxApp`` is
        wired up; "custom" backend raises a click error and exits.

    Raises:
        SystemExit: If the backend is unavailable or unknown.
    """
    if backend == "libtmux":
        try:
            from meshterm.libtmux_session import LibtmuxApp
            return LibtmuxApp()
        except ImportError:
            click.echo("Error: libtmux not installed. Run: pip install meshterm[backend-tmux]", err=True)
            sys.exit(1)
    elif backend == "custom":
        click.echo("Error: custom backend CLI not yet implemented (use Python API)", err=True)
        sys.exit(1)
    else:
        click.echo(f"Error: unknown backend '{backend}'. Use 'libtmux' or 'custom'.", err=True)
        sys.exit(1)


# ── Main group ──

@click.group()
@click.option("--backend", "-b", default="libtmux", type=click.Choice(["libtmux", "custom"]),
              help="Backend to use (default: libtmux)")
@click.version_option(package_name="meshterm", prog_name="meshterm")
@click.pass_context
def app(ctx, backend: str) -> None:
    """meshterm -- programmatic terminal control for Linux.

    iTerm2-compatible API for tmux sessions.
    """
    ctx.ensure_object(dict)
    ctx.obj["backend"] = backend


# -- meshterm init-config --

@app.command(name="init-config")
@click.option(
    "--mode",
    type=click.Choice(["from-template", "interactive", "validate"]),
    default="from-template",
    show_default=True,
    help="from-template: copy bundled local.toml.template to ~/.config/meshterm/local.toml; "
         "interactive: prompt for values; validate: parse + report errors.",
)
@click.option("--force", is_flag=True, help="Overwrite existing local.toml without asking")
def init_config(mode: str, force: bool) -> None:
    """Bootstrap or validate ~/.config/meshterm/local.toml (chmod 600 enforced)."""
    import os
    import shutil
    from pathlib import Path

    target = Path.home() / ".config" / "meshterm" / "local.toml"
    target.parent.mkdir(parents=True, exist_ok=True)

    if mode == "validate":
        if not target.exists():
            click.secho(f"validate: {target} does not exist; nothing to validate.", fg="yellow")
            return
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
            with target.open("rb") as fh:
                data = tomllib.load(fh)
            click.secho(f"validate: {target} parsed OK ({len(data)} top-level sections)", fg="green")
            for k in sorted(data.keys()):
                click.echo(f"  {k}")
        except Exception as exc:
            click.secho(f"validate: ERROR {exc}", fg="red")
            sys.exit(2)
        return

    if target.exists() and not force:
        click.secho(f"{target} already exists. Use --force to overwrite.", fg="yellow")
        sys.exit(1)

    template = None
    for candidate in [
        Path(__file__).parent / "templates" / "local.toml.template",
        Path(__file__).parent.parent.parent / "meshterm.toml.example",
    ]:
        if candidate.exists():
            template = candidate
            break
    if template is None:
        target.write_text(
            "# meshterm local config (chmod 600)\n"
            "[meshterm]\nbackend = \"libtmux\"\n\n"
            "[ipc]\nsocket_path = \"~/.local/state/meshterm/ipc.sock\"\n"
        )
    else:
        shutil.copyfile(str(template), str(target))

    os.chmod(target, 0o600)
    click.secho(f"Wrote {target} (chmod 600)", fg="green")

    if mode == "interactive":
        click.echo("Interactive setup is not yet wired; edit the file manually for now:")
        click.echo(f"  $EDITOR {target}")


# ── meshterm status ──

@app.command()
@click.option("--idle/--no-idle", default=True,
              help="Run idle detection (polls 3x at 1s intervals)")
@click.pass_context
def status(ctx, idle: bool) -> None:
    """List all tmux sessions with IDLE/BUSY state."""
    backend = get_backend(ctx.obj["backend"])
    sessions = backend.list_sessions()

    if not sessions:
        click.echo("No sessions found.")
        return

    # Run idle detection if requested
    idle_states = {}
    idle_hashes = {}
    if idle:
        from meshterm.idle import IdleChecker, IdleCheckerConfig, IdleState
        config = IdleCheckerConfig(min_stable_polls=2)
        checkers: dict[str, IdleChecker] = {}
        sessions_list = sessions

        # Poll 3 times to establish baseline + detect idle
        for _ in range(3):
            for sess in sessions_list:
                pid = sess.pane_id
                if pid not in checkers:
                    checkers[pid] = IdleChecker(config=config)
                screen_lines = sess._pane.capture_pane()
                result = checkers[pid].check(screen_lines)
                idle_states[pid] = result
                idle_hashes[pid] = result.screen_hash[:12]
            time.sleep(1.0)

    if RICH_AVAILABLE:
        table = Table(title="meshterm sessions")
        table.add_column("UUID", style="dim", max_width=12)
        table.add_column("Pane", style="cyan")
        table.add_column("State", style="bold")
        table.add_column("Command", style="green")
        table.add_column("Idle", justify="right")
        table.add_column("Hash", style="dim", max_width=12)
        table.add_column("PID", justify="right")
        table.add_column("CWD", style="blue")

        for s in sessions:
            ist = idle_states.get(s.pane_id)
            if ist:
                if ist.state.value == "IDLE":
                    state_str = "[green]IDLE[/green]"
                elif ist.state.value == "UNKNOWN":
                    state_str = "[dim]?[/dim]"
                else:
                    state_str = "[red]BUSY[/red]"
                idle_str = f"{ist.idle_seconds:.0f}s" if ist.idle_seconds > 0 else "-"
                hash_str = idle_hashes.get(s.pane_id, "-")
            else:
                state_str = "[dim]?[/dim]"
                idle_str = "-"
                hash_str = "-"

            table.add_row(
                s.uuid[:12],
                s.pane_id,
                state_str,
                s.current_command,
                idle_str,
                hash_str,
                str(s.pid),
                s.cwd,
            )
        console.print(table)

        # Summary line
        from meshterm.idle import IdleState
        idle_count = sum(1 for s in idle_states.values() if s.state == IdleState.IDLE)
        total = len(sessions)
        console.print(f"  {idle_count}/{total} sessions IDLE")
    else:
        click.echo(f"{'UUID':<14} {'Pane':<8} {'State':<7} {'Command':<15} {'Hash':<14} {'PID':<8} {'CWD'}")
        click.echo("-" * 90)
        for s in sessions:
            ist = idle_states.get(s.pane_id)
            state = ist.state.value if ist else "?"
            hash_str = idle_hashes.get(s.pane_id, "-")
            click.echo(f"{s.uuid[:12]:<14} {s.pane_id:<8} {state:<7} {s.current_command:<15} {hash_str:<14} {s.pid:<8} {s.cwd}")


# ── meshterm send ──

@app.command()
@click.argument("session")
@click.argument("text", required=False)
@click.option("--enter/--no-enter", default=False, help="Press Enter after text")
@click.option("--from-file", "from_file",
              type=click.Path(exists=True, dir_okay=False, readable=True),
              help="Read text from FILE (apostrophe-safe, bypasses shell quoting). "
                   "Use this for any text containing embedded apostrophes or "
                   "shell metacharacters that would otherwise need escaping.")
@click.option("--from-stdin", "from_stdin", is_flag=True,
              help="Read text from stdin (pipe). Apostrophe-safe.")
@click.pass_context
def send(ctx, session: str, text: Optional[str], enter: bool,
         from_file: Optional[str], from_stdin: bool) -> None:
    """Send text to a session.

    SESSION can be a session name or UUID prefix.

    Text source (exactly one required):
      TEXT positional      simple text (breaks on shell-embedded apostrophes)
      --from-file PATH     read from file (apostrophe-safe canonical)
      --from-stdin         read from stdin (pipe-based, apostrophe-safe)
    """
    sources = [bool(text), bool(from_file), bool(from_stdin)]
    if sum(sources) == 0:
        click.echo("Error: must provide TEXT, --from-file, or --from-stdin.",
                   err=True)
        sys.exit(2)
    if sum(sources) > 1:
        click.echo("Error: only one of TEXT, --from-file, --from-stdin allowed.",
                   err=True)
        sys.exit(2)

    if from_file:
        text = Path(from_file).read_text(encoding="utf-8")
    elif from_stdin:
        text = sys.stdin.read()

    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    sess.send_text(text, enter=enter)
    preview = text if len(text) <= 80 else text[:77] + "..."
    click.echo(f"Sent to {sess.pane_id}: {preview!r}" + (" + Enter" if enter else ""))


# ── meshterm key ──

@app.command()
@click.argument("session")
@click.argument("key")
@click.pass_context
def key(ctx, session: str, key: str) -> None:
    """Send a special key to a session.

    KEY can be: Enter, Escape, C-c, Tab, BSpace, Up, Down, Left, Right
    """
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    sess.send_key(key)
    click.echo(f"Sent key '{key}' to {sess.pane_id}")


# ── meshterm read ──

@app.command()
@click.argument("session")
@click.option("--raw", is_flag=True, help="Raw output without formatting")
@click.pass_context
def read(ctx, session: str, raw: bool) -> None:
    """Read screen content from a session."""
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    screen = sess.read_screen()

    if raw:
        for line in screen.lines:
            click.echo(line.string)
    else:
        if RICH_AVAILABLE:
            console.print(f"[bold]Screen[/bold] {sess.pane_id} ({screen.number_of_lines} lines, cursor: {screen.cursor_x},{screen.cursor_y})")
            console.print("─" * 60)
        else:
            click.echo(f"Screen {sess.pane_id} ({screen.number_of_lines} lines)")
            click.echo("─" * 60)
        for line in screen.lines:
            click.echo(line.string)


# ── meshterm wait ──

@app.command()
@click.argument("session")
@click.argument("pattern")
@click.option("--timeout", "-t", default=30.0, help="Timeout in seconds")
@click.option("--interval", "-i", default=0.5, help="Poll interval in seconds")
@click.pass_context
def wait(ctx, session: str, pattern: str, timeout: float, interval: float) -> None:
    """Wait for a pattern to appear on screen.

    Returns exit code 0 if found, 1 if timeout.
    """
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    click.echo(f"Waiting for '{pattern}' (timeout: {timeout}s)...")
    result = sess.wait_for(pattern, timeout=timeout, interval=interval)

    if result:
        click.echo(f"Found: {result}")
        sys.exit(0)
    else:
        click.echo(f"Timeout: pattern '{pattern}' not found after {timeout}s", err=True)
        sys.exit(1)


# ── meshterm create ──

@app.command()
@click.argument("name")
@click.option("--command", "-c", default=None, help="Command to run in session")
@click.pass_context
def create(ctx, name: str, command: Optional[str]) -> None:
    """Create a new tmux session."""
    backend = get_backend(ctx.obj["backend"])
    sess = backend.create_session(name=name, command=command)
    click.echo(f"Created session: {name} (uuid: {sess.uuid[:12]}, pane: {sess.pane_id})")


# ── meshterm kill ──

@app.command()
@click.argument("session")
@click.pass_context
def kill(ctx, session: str) -> None:
    """Kill a session."""
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    pane_id = sess.pane_id
    sess.close()
    click.echo(f"Killed session {pane_id}")


# ── meshterm diff ──

@app.command()
@click.argument("session")
@click.pass_context
def diff(ctx, session: str) -> None:
    """Show screen changes since last read."""
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    # First read to establish baseline
    sess.read_screen()
    click.echo("Baseline captured. Run again to see diff.")
    d = sess.screen_diff()
    if d["is_idle"]:
        click.echo("No changes.")
    else:
        click.echo(f"Changed lines: {d['lines_changed']}")
        for line in d["added"]:
            click.echo(f"  + {line}")
        for line in d["removed"]:
            click.echo(f"  - {line}")


# ── meshterm exec ──

@app.command(name="exec")
@click.argument("session")
@click.argument("command")
@click.option("--wait-for", "-w", default=None, help="Pattern to wait for after execution")
@click.option("--timeout", "-t", default=30.0, help="Timeout for --wait-for")
@click.pass_context
def exec_cmd(ctx, session: str, command: str, wait_for: Optional[str], timeout: float) -> None:
    """Execute a command in session (send + Enter + optional wait).

    This is the most common workflow: send command, press Enter, optionally
    wait for output pattern.
    """
    backend = get_backend(ctx.obj["backend"])
    sess = _find_session(backend, session)
    if not sess:
        click.echo(f"Error: session '{session}' not found.", err=True)
        sys.exit(1)

    sess.send_command(command)
    click.echo(f"Executed: {command}")

    if wait_for:
        click.echo(f"Waiting for '{wait_for}'...")
        result = sess.wait_for(wait_for, timeout=timeout)
        if result:
            click.echo(f"Found: {result}")
        else:
            click.echo(f"Timeout waiting for '{wait_for}'", err=True)
            sys.exit(1)


# ── meshterm monitor ──

@app.command()
@click.option("--interval", "-i", default=5.0, help="Poll interval in seconds")
@click.option("--threshold", "-t", default=900.0, help="Idle threshold in seconds (default: 900 = 15 min)")
@click.option("--on-idle", default=None, help="Shell command to run when all sessions idle")
@click.option("--log", default=None, help="Log idle events to file")
@click.option("--webhook", default=None, help="HTTP URL to POST when all sessions idle")
@click.option("--once", is_flag=True, default=False,
              help="Poll 3 times and exit (no daemon loop)")
@click.pass_context
def monitor(ctx, interval: float, threshold: float, on_idle: Optional[str],
            log: Optional[str], webhook: Optional[str], once: bool) -> None:
    """Continuous idle monitoring with cron trigger.

    Watches all sessions, shows live IDLE/BUSY state, and triggers
    callbacks when all sessions have been idle past the threshold.

    Examples:

        meshterm monitor                           # default: 5s poll, 15min trigger

        meshterm monitor --once                    # single snapshot (3 polls, exit)

        meshterm monitor -t 60                     # trigger after 1 min idle

        meshterm monitor --on-idle "echo IDLE"     # run command on idle

        meshterm monitor --webhook https://hooks.example.com/idle

        meshterm monitor --log /tmp/idle.log       # log idle events
    """
    backend = get_backend(ctx.obj["backend"])

    from meshterm.monitor import Monitor, MonitorConfig, make_shell_trigger, make_log_trigger, make_webhook_trigger

    config = MonitorConfig(
        poll_interval=interval,
        idle_threshold=threshold,
        min_idle_polls=2 if once else 3,
    )
    mon = Monitor(backend, config=config)

    # Register triggers
    if on_idle:
        mon.on_trigger(make_shell_trigger(on_idle))
        click.echo(f"Trigger registered: {on_idle}")

    if log:
        mon.on_trigger(make_log_trigger(log))
        click.echo(f"Logging to: {log}")

    if webhook:
        mon.on_trigger(make_webhook_trigger(webhook))
        click.echo(f"Webhook registered: {webhook}")

    # ── --once mode: poll 3 times, print table, exit ──
    if once:
        from meshterm.monitor import SessionState
        click.echo(f"meshterm monitor --once — polling 3x at {interval}s intervals\n")
        statuses = []
        for i in range(3):
            statuses = mon.poll_once()
            if i < 2:
                time.sleep(interval)

        if not statuses:
            click.echo("No sessions found.")
            return

        if RICH_AVAILABLE:
            table = Table(title="meshterm monitor (snapshot)")
            table.add_column("Pane", style="cyan")
            table.add_column("State", style="bold")
            table.add_column("Command", style="green")
            table.add_column("Idle", justify="right")
            table.add_column("Hash", style="dim", max_width=16)
            table.add_column("Preview", style="dim", max_width=40)

            for s in statuses:
                state_str = (
                    "[green]IDLE[/green]" if s.state == SessionState.IDLE
                    else "[red]BUSY[/red]"
                )
                idle_str = f"{s.idle_seconds:.0f}s" if s.idle_seconds > 0 else "-"
                table.add_row(
                    s.pane_id, state_str, s.command,
                    idle_str, s.screen_hash, s.screen_preview[:40],
                )
            console.print(table)
        else:
            click.echo(f"{'Pane':<8} {'State':<6} {'Command':<15} {'Idle':<8} {'Hash':<18} {'Preview'}")
            click.echo("-" * 80)
            for s in statuses:
                idle_str = f"{s.idle_seconds:.0f}s" if s.idle_seconds > 0 else "-"
                click.echo(
                    f"{s.pane_id:<8} {s.state.value:<6} {s.command:<15} "
                    f"{idle_str:<8} {s.screen_hash:<18} {s.screen_preview[:40]}"
                )

        idle_count = sum(1 for s in statuses if s.state == SessionState.IDLE)
        click.echo(f"\n  {idle_count}/{len(statuses)} sessions IDLE")
        all_dur = mon.all_idle_duration()
        if all_dur > 0:
            click.echo(f"  All idle for {all_dur:.0f}s (trigger at {threshold:.0f}s)")
        return

    # ── Daemon mode ──

    # Built-in trigger: print to console
    def console_trigger(idle_seconds, sessions) -> None:
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        names = ", ".join(s.name for s in sessions)
        if RICH_AVAILABLE:
            console.print(f"\n[bold red]>>> TRIGGER[/bold red] [{ts}] All {len(sessions)} sessions IDLE for {idle_seconds:.0f}s ({names})")
        else:
            click.echo(f"\n>>> TRIGGER [{ts}] All {len(sessions)} sessions IDLE for {idle_seconds:.0f}s ({names})")

    mon.on_trigger(console_trigger)

    # Per-session state change logging
    def on_sess_idle(status) -> None:
        if RICH_AVAILABLE:
            console.print(f"  [green]IDLE[/green] {status.pane_id} ({status.name}) idle for {status.idle_seconds:.0f}s")
        else:
            click.echo(f"  IDLE {status.pane_id} ({status.name})")

    def on_sess_busy(status) -> None:
        if RICH_AVAILABLE:
            console.print(f"  [red]BUSY[/red] {status.pane_id} ({status.name}) screen changed")
        else:
            click.echo(f"  BUSY {status.pane_id} ({status.name})")

    mon.on_session_idle(on_sess_idle)
    mon.on_session_busy(on_sess_busy)

    # Header
    click.echo(f"meshterm monitor — polling every {interval}s, trigger after {threshold}s idle")
    click.echo("Press Ctrl+C to stop.\n")

    # Blocking loop with live display
    try:
        poll_count = 0
        while True:
            statuses = mon.poll_once()
            poll_count += 1

            # Periodic status summary (every 12 polls = ~1 minute at 5s interval)
            if poll_count % max(1, int(60 / interval)) == 0:
                idle_count = sum(1 for s in statuses if s.state.value == "IDLE")
                total = len(statuses)
                all_idle_dur = mon.all_idle_duration()
                remaining = max(0, threshold - all_idle_dur) if all_idle_dur > 0 else threshold

                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")

                if RICH_AVAILABLE:
                    line = f"[dim][{ts}][/dim] {idle_count}/{total} IDLE"
                    if all_idle_dur > 0:
                        line += f" | all idle {all_idle_dur:.0f}s | trigger in {remaining:.0f}s"
                    console.print(line)
                else:
                    line = f"[{ts}] {idle_count}/{total} IDLE"
                    if all_idle_dur > 0:
                        line += f" | all idle {all_idle_dur:.0f}s | trigger in {remaining:.0f}s"
                    click.echo(line)

            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nMonitor stopped.")


# ── meshterm vscode-profile ──

@app.group(name="vscode-profile")
def vscode_profile() -> None:
    """Manage VS Code terminal profiles for meshterm/tmux colony sessions.

    Generates 3 terminal profiles per worker (main / attach / new) with
    optional conda-env activation, the colony color convention (nova=cyan,
    forge=red, sentinel=green, weaver=blue), and stable tab names via
    ``overrideName``. The profiles let Dr. Umit pick a worker from the
    VS Code terminal dropdown and get a live view of its tmux session.

    See ``docs/VSCODE.md`` for the full mental model.
    """


@vscode_profile.command(name="add")
@click.argument("session")
@click.option(
    "--workspace", "-w", required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a VS Code .code-workspace file",
)
@click.option(
    "--conda-env", default="claude_mesh",
    help="Conda environment to activate in profiles (default: claude_mesh)",
)
@click.option(
    "--conda-base", default="~/miniconda3",
    help="Conda installation root (default: ~/miniconda3)",
)
@click.option(
    "--no-conda", is_flag=True,
    help="Skip conda activation — produce plain-bash profiles",
)
@click.option(
    "--color", default=None,
    help="Override color (e.g. terminal.ansiMagenta). Default: colony convention",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Preview changes without modifying the workspace file",
)
@click.option(
    "--no-backup", is_flag=True,
    help="Skip creating a .bak copy before modifying the workspace file",
)
@click.option(
    "--no-tmux", is_flag=True,
    help="Skip creating the tmux session (assume it already exists)",
)
def vscode_profile_add(
    session: str,
    workspace: Path,
    conda_env: str,
    conda_base: str,
    no_conda: bool,
    color: Optional[str],
    dry_run: bool,
    no_backup: bool,
    no_tmux: bool,
) -> None:
    """Add 3 VS Code terminal profiles for a worker.

    SESSION is the worker name (e.g. nova, forge, sentinel, weaver).

    Adds three profiles idempotently:

    \b
        {session}-tmux   - main (attach-or-create, safe default)
        {Name}-Claude    - strict attach (errors if missing)
        {Name}-New       - parallel scratch session

    The workspace file is modified atomically; a .bak copy is written
    unless --no-backup is set.
    """
    from meshterm.vscode_profiles import (
        add_profiles_to_workspace,
        ensure_tmux_session,
    )

    click.echo(f"[meshterm] Adding '{session}' profiles to {workspace.name}...")

    if not no_tmux:
        if ensure_tmux_session(session):
            click.echo(f"  tmux session '{session}': ok")
        else:
            click.echo(
                f"  tmux session '{session}': FAILED "
                "(tmux not installed or could not be created)",
                err=True,
            )

    effective_env = None if no_conda else conda_env
    ok, msg = add_profiles_to_workspace(
        workspace,
        session,
        conda_env=effective_env,
        conda_base=conda_base,
        color=color,
        dry_run=dry_run,
        backup=not no_backup,
    )

    if ok:
        click.echo(f"  {msg}")
        if not dry_run and not no_backup:
            click.echo(f"  backup: {workspace}.bak")
    else:
        click.echo(f"  ERROR: {msg}", err=True)
        sys.exit(1)


@vscode_profile.command(name="list")
@click.option(
    "--workspace", "-w", required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a VS Code .code-workspace file",
)
def vscode_profile_list(workspace: Path) -> None:
    """List all VS Code terminal profiles in a workspace file."""
    from meshterm.vscode_profiles import list_profiles_in_workspace

    profiles = list_profiles_in_workspace(workspace)
    if not profiles:
        click.echo(f"No profiles found in {workspace.name}.")
        return

    click.echo(f"\nTerminal profiles in {workspace.name}:")
    for name, ptype in profiles:
        click.echo(f"  {name:25s} ({ptype})")


@vscode_profile.command(name="status")
def vscode_profile_status() -> None:
    """Show tmux sessions and meshterm CLI availability."""
    from meshterm.vscode_profiles import colony_status

    status = colony_status()
    click.echo("\n=== tmux sessions ===")
    click.echo(status["tmux"])
    click.echo("\n=== meshterm CLI ===")
    click.echo(status["meshterm"])


# ── Helper: find session by name or UUID prefix ──

def _find_session(backend, identifier: str):
    """Find session by name match or UUID prefix."""
    # Try name match first
    sess = backend.get_session_by_name(identifier)
    if sess:
        return sess

    # Try UUID prefix
    for s in backend.list_sessions():
        if s.uuid.startswith(identifier):
            return s

    return None


# ── Entry point ──

if __name__ == "__main__":
    app()
