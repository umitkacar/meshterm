# AI Chat & Codecierge

> Built-in AI assistant with full terminal session awareness and 7 permission categories.
>
> **Available in:** iTerm2 3.5+ | **Enhanced in:** 3.6.x

---

## Overview

iTerm2 includes a fully integrated AI chat assistant that can be linked to terminal sessions. Unlike standalone AI tools, iTerm2's AI Chat has deep terminal context awareness — it can read your command history, check terminal state, run commands, and even interact with web pages.

---

## Access

| Action | Shortcut / Location |
|--------|---------------------|
| **Open AI Chat** | Window → AI Chat |
| **Session-linked Chat** | Session → Open AI Chat |
| **Explain Output** | Edit → Explain Output with AI |
| **Engage AI** | Edit → Engage Artificial Intelligence |
| **Settings** | Settings → General → AI |

---

## AI Chat Features

### Session-Linked Chats

Chats can be either standalone or linked to a specific terminal session. Linked chats gain context about:

- Current working directory
- Shell type and version
- Command history
- Exit status of commands
- Window dimensions
- SSH host and username

### 8 Permission Categories

Each permission can be cycled: **Never → Ask → Always** (per chat)

| Permission | What It Allows |
|------------|----------------|
| **Check Terminal State** | Read directory, shell type, history, SSH host, window dimensions |
| **Run Commands** | Execute terminal commands on your behalf |
| **Type for You** | Send keystrokes to the terminal |
| **View History** | Access command history from linked session |
| **View Manpages** | Access man pages (including remote via SSH integration) |
| **Write to Clipboard** | Modify clipboard contents |
| **Write to Filesystem** | File system modifications |
| **Act in Web Browser** | View and interact with web page content |

### Toolbar Controls

| Icon | Function |
|------|----------|
| **Model Selector** | Choose AI model from available options |
| **Globe** | Grant web search permission |
| **Lightbulb** | Enable reasoning mode (slower but more thorough) |

### Message Management

- **Right-click** on messages to edit, copy, or fork conversations
- **Auto-send** option sends terminal contents to AI automatically
- **Linked sessions** provide real-time context updates

---

## Codecierge

A specialized AI assistant available in the Toolbelt.

| Aspect | Details |
|--------|---------|
| **Access** | View → Toolbelt → Codecierge |
| **Purpose** | Intelligent code assistance within terminal context |
| **Integration** | Works alongside active terminal sessions |

---

## AI + Composer Integration

The Composer feature integrates with AI for command suggestions:

```
Settings → General → AI
  ☑ Offer AI command suggestion in Composer and Auto Composer
```

This provides inline AI-powered command completions as you type in the Composer.

---

## Configuration

### Settings → General → AI

| Setting | Description |
|---------|-------------|
| **Plugin Installation** | Install required AI plugin |
| **Consent** | Manage AI consent preferences |
| **API Key** | Configure API key for AI service |
| **Recommended Model** | Auto-select recommended model |
| **Timeout** | Configure AI response timeout |
| **Manual Config** | Custom model name, token limit, endpoint URL, API style |

### Custom Endpoint

For self-hosted or alternative AI providers:

| Field | Description |
|-------|-------------|
| Model Name | Name of the model |
| Token Limit | Maximum token count |
| Endpoint URL | API endpoint |
| API Style | API protocol/format |

---

## Use Cases

### 1. Command Help
Ask "How do I find files larger than 100MB?" → AI suggests `find / -size +100M`

### 2. Output Explanation
Select confusing output → Edit → Explain Output with AI → Get annotated explanation

### 3. Debugging
"Why did my last command fail?" → AI checks exit status, reads error output, suggests fix

### 4. Scripting
"Write a bash script that monitors disk usage" → AI generates and can execute the script

---

## Related Documentation

- [Composer](./all-features.md#34-composer--auto-composer)
- [Triggers](./triggers.md)
- [Python API](../03-scripting/python-api-guide.md)
