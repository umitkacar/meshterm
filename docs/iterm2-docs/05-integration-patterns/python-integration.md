# Python + iTerm2 Integration

> Native Python integration with iTerm2 API.

---

## Setup

```bash
pip install iterm2
```

Enable in iTerm2:
```
Settings → General → Magic → Enable Python API
```

---

## Basic Pattern

```python
#!/usr/bin/env python3
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    # Your automation here

iterm2.run_until_complete(main)
```

---

## CLI Tool Pattern

```python
#!/usr/bin/env python3
import iterm2
import argparse

async def main(connection, args):
    app = await iterm2.async_get_app(connection)

    if args.new_window:
        window = await iterm2.Window.async_create(connection)
        session = window.current_tab.current_session
    else:
        session = app.current_window.current_tab.current_session

    if args.command:
        await session.async_send_text(f"{args.command}\n")

    if args.name:
        await session.async_set_name(args.name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--new-window", action="store_true")
    parser.add_argument("-c", "--command")
    parser.add_argument("--name")
    args = parser.parse_args()

    iterm2.run_until_complete(lambda c: main(c, args))
```

---

## Script as Module

```python
# iterm_utils.py
import iterm2

async def create_window_with_command(connection, command, name=None):
    window = await iterm2.Window.async_create(connection)
    session = window.current_tab.current_session

    if name:
        await session.async_set_name(name)

    if command:
        await session.async_send_text(f"{command}\n")

    return window, session
```

```python
# main.py
import iterm2
from iterm_utils import create_window_with_command

async def main(connection):
    window, session = await create_window_with_command(
        connection,
        "npm run dev",
        "Development"
    )

iterm2.run_until_complete(main)
```

---

## Related Documentation

- [Python API Guide](../03-scripting/python-api-guide.md)
- [Bash Integration](./bash-integration.md)
