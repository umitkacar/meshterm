"""meshterm -- Linux terminal emulator with iTerm2-compatible programmatic control.

Provides a Python API that mirrors iTerm2's scripting interface, enabling
programmatic terminal control on Linux via Unix domain socket IPC.

Quick start:

    import meshterm

    async def main():
        async with meshterm.Connection.unix() as conn:
            app = await meshterm.async_get_app(conn)
            session = app.current_window.current_tab.current_session
            await session.async_send_text("echo hello\\n")
            contents = await session.async_get_screen_contents()
            for line in contents.lines:
                print(line.string)

    meshterm.run_until_complete(main)
"""

from typing import Any, Callable, Coroutine

from meshterm.connection import Connection
from meshterm.app import MeshTermApp, async_get_app
from meshterm.session import MeshTermSession, ScreenContents, ScreenLine
from meshterm.window import MeshTermWindow
from meshterm.tab import MeshTermTab
from meshterm.server import MeshTermServer
from meshterm.idle import IdleChecker, IdleCheckerConfig, IdleState, IdleResult
from meshterm.monitor import Monitor, MonitorConfig
from meshterm.jsonl_history import JsonlHistory, ToolCall, ThinkingBlock, Message
from meshterm.bash_history import BashHistory
from meshterm.remote import RemoteMeshTerm

__version__ = "0.2.11"

__all__ = [
    "Connection",
    "MeshTermApp",
    "MeshTermSession",
    "MeshTermWindow",
    "MeshTermTab",
    "MeshTermServer",
    "ScreenContents",
    "ScreenLine",
    "IdleChecker",
    "IdleCheckerConfig",
    "IdleState",
    "IdleResult",
    "Monitor",
    "MonitorConfig",
    "JsonlHistory",
    "ToolCall",
    "ThinkingBlock",
    "Message",
    "BashHistory",
    "RemoteMeshTerm",
    "async_get_app",
    "run_until_complete",
]


def run_until_complete(coro_func: Callable[[], Coroutine[Any, Any, Any]]) -> None:
    """Convenience wrapper: create event loop and run an async function.

    Mirrors iterm2.run_until_complete() — the standard entrypoint
    for iTerm2 scripts. Meshterm equivalent works identically:

        import meshterm

        async def main():
            async with meshterm.Connection.unix() as conn:
                app = await meshterm.async_get_app(conn)
                ...

        meshterm.run_until_complete(main)
    """
    import asyncio
    asyncio.run(coro_func())
