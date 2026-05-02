# Terminal Emulators Comparison (2026)

> Comparing iTerm2 with alternative terminal emulators for macOS.
>
> **Updated:** 2026-03-23 | **iTerm2 Version:** 3.6.9

---

## Overview

| Terminal | Language | GPU | License | Stars | Status |
|----------|----------|-----|---------|-------|--------|
| **iTerm2** | Obj-C/Swift | Metal | GPLv2+ | 16.7k+ | Active |
| **Ghostty** | Zig | Metal/Vulkan | MIT | 30k+ | Active (NEW) |
| **Alacritty** | Rust | OpenGL | Apache 2.0 | 57k+ | Active |
| **Kitty** | C/Python | OpenGL | GPLv3 | 25k+ | Active |
| **Warp** | Rust | Metal | Proprietary | 20k+ | Active |
| **WezTerm** | Rust | OpenGL | MIT | 18k+ | Active |
| **Rio** | Rust | WebGPU/WGPU | MIT | 4k+ | Active (NEW) |
| **Hyper** | Electron | - | MIT | 43k | Maintenance |
| **Terminal.app** | - | - | macOS | - | Redesigned (Tahoe!) |

---

## Feature Comparison

| Feature | iTerm2 | Ghostty | Alacritty | Kitty | Warp | WezTerm | Rio |
|---------|--------|---------|-----------|-------|------|---------|-----|
| **Split Panes** | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Tabs** | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **GPU Render** | ✅ Metal | ✅ Metal | ✅ OpenGL | ✅ OpenGL | ✅ Metal | ✅ OpenGL | ✅ WebGPU |
| **Ligatures** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **24-bit Color** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Images** | ✅ | ✅ Kitty | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Scripting** | Python (30) | ❌ | ❌ | Python | ❌ | Lua | ❌ |
| **tmux Integration** | ✅ Native | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Shell Integration** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| **AI Chat** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Session Recording** | ✅ asciinema | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Window Projects** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cross-platform** | macOS | macOS/Linux | All | All | macOS/Linux | All | All |

---

## Performance

| Terminal | Startup | RAM | Render Speed | Notes |
|----------|---------|-----|-------------|-------|
| **Ghostty** | ⚡ 30ms | 25MB | Fastest | Zig + Metal, zero-copy |
| **Alacritty** | ⚡ 50ms | 30MB | Very Fast | Minimal feature set |
| **Kitty** | ⚡ 80ms | 50MB | Very Fast | Good balance |
| **Rio** | ⚡ 60ms | 35MB | Fast | WebGPU rendering |
| **WezTerm** | 100ms | 80MB | Fast | Feature-rich |
| **iTerm2** | 150ms | 100MB | Good | Most features |
| **Warp** | 200ms | 150MB | Fast | AI overhead |
| **Hyper** | 500ms | 200MB | Slow | Electron-based |

---

## New Contenders (2025-2026)

### Ghostty

Created by **Mitchell Hashimoto** (founder of HashiCorp — Terraform, Vagrant, Vault). Non-profit under Hack Club 501(c)(3).

| Aspect | Details |
|--------|---------|
| **Version** | 1.3.1 (March 13, 2026) |
| **Language** | Zig (performance-focused systems language) |
| **GPU** | Metal (macOS), OpenGL (Linux) |
| **License** | MIT (open source Dec 2024) |
| **Platforms** | macOS, Linux (Windows planned) |
| **Performance** | ~407 FPS render, ~2ms key-to-screen latency |
| **Config** | Simple key=value text config |
| **Stars** | 30,000+ (fastest growing terminal project) |

**Why Ghostty Matters:**
- Built from scratch with zero legacy baggage
- Uses Zig for memory safety without GC overhead
- Native macOS app (not Electron, not Rust bindings)
- Kitty graphics + keyboard protocol support
- Quick Terminal (dropdown from menu bar)
- Hundreds of built-in themes with auto dark/light switching
- Scrollback search (new in 1.3)
- AppleScript support on macOS
- 180+ contributors, 2,858 commits in 1.3.0 alone
- Very active community and development

### Rio

| Aspect | Details |
|--------|---------|
| **Version** | 0.2.37 (March 2026) |
| **Language** | Rust |
| **GPU** | WebGPU/WGPU (Metal, Vulkan, DX11/DX12, OpenGL ES, WebGL) |
| **License** | MIT |
| **Platforms** | macOS, Linux, Windows, FreeBSD, browser (WASM planned) |
| **Key Feature** | Custom shaders (RetroArch CRT), SIMD-accelerated UTF-8 |

---

## When to Use What (2026 Updated)

| Use Case | Recommendation | Why |
|----------|----------------|-----|
| **Maximum features** | iTerm2 | 39+ features, AI Chat, Window Projects, 30-module API |
| **Maximum speed** | Ghostty | Zig + Metal, fastest startup |
| **Speed + features** | Kitty | Good balance, Python scripting |
| **AI-powered** | iTerm2 or Warp | Built-in AI assistants |
| **Cross-platform** | WezTerm or Kitty | Linux + macOS + Windows |
| **Minimal + fast** | Alacritty + tmux | No bloat, pure terminal |
| **Modern UI** | Warp | Block-based terminal |
| **Session recording** | iTerm2 | Built-in multi-format logging |
| **Window archiving** | iTerm2 | Window Projects (unique feature) |
| **Scripting/Automation** | iTerm2 | 30-module Python API (unmatched) |

---

## Scripting Comparison

| Terminal | API Type | Languages | Modules |
|----------|----------|-----------|---------|
| **iTerm2** | WebSocket | Python | 30 |
| **Kitty** | Kitten/Remote | Python | 10+ |
| **WezTerm** | Built-in | Lua | Config-based |
| **Ghostty** | None (planned?) | - | - |
| **Alacritty** | None | - | - |
| **Warp** | Limited CLI | - | - |
| **Rio** | None | - | - |

---

## Session Recording Comparison

| Terminal | Format | Timing | Playback | Export |
|----------|--------|--------|----------|--------|
| **iTerm2** | Raw/Text/HTML/asciinema | ✅ | ✅ asciinema | ✅ |
| **Others** | ❌ (use external tools) | - | - | - |

External alternatives: `asciinema`, `script`, `ttyrec`, `terminalizer`

---

## Related Documentation

- [Automation Approaches](./automation-approaches.md)
- [When to Use What](./when-to-use-what.md)
- [iTerm2 AI Chat](../02-features-reference/ai-chat.md)
