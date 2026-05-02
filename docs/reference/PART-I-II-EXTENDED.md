# Building Terminal Emulators from Scratch

## A Comprehensive Technical Guide for Experienced Developers

---

# PART I: FOUNDATIONS

---

## Chapter 1: What Is a Terminal?

Before writing a single line of code, you need to understand what a terminal actually is--and what it is not. The terms "terminal," "shell," and "console" are used interchangeably in casual conversation, but they refer to fundamentally different things. Conflating them will sabotage your architecture from day one.

### 1.1 Terminal vs Shell vs Console

**Terminal** (or terminal emulator): A program that provides a text-based input/output interface. It handles keyboard input, escape sequence parsing, character cell rendering, and display. The terminal does not execute commands--it delegates that to a shell running inside it. Historically, a terminal was a physical hardware device (the DEC VT100, for instance). Today, it is software emulating that hardware. Examples: Alacritty, Ghostty, Windows Terminal, iTerm2, GNOME Terminal.

**Shell**: An interpreter that reads commands and executes them. The shell runs *inside* a terminal. It provides the prompt, environment variables, scripting, job control, and command execution. Examples: bash, zsh, fish, PowerShell, sh. You can run a shell without a terminal (in a script) and a terminal without a traditional shell (by launching `python` or `vim` directly).

**Console**: Originally the physical operator station--the hardware panel attached to a mainframe. On Linux, the console refers to the kernel's built-in text interface (`/dev/console`, the virtual consoles on Ctrl+Alt+F1-F6). On Windows, the "Console Host" (`conhost.exe`) is the legacy system that renders console applications. The console is the system-level I/O facility; a terminal emulator replaces or wraps it.

The relationship is layered:

```
+-----------------------------------------------+
|  Terminal Emulator  (display + input + PTY)    |
|  +-------------------------------------------+|
|  |  Shell  (bash, zsh, fish)                 ||
|  |  +---------------------------------------+||
|  |  |  Programs  (ls, grep, vim, python)    |||
|  |  +---------------------------------------+||
|  +-------------------------------------------+||
+-----------------------------------------------+
```

*Reference diagram: ![Terminal vs Shell vs Console](assets/05-terminal-shell-console.svg)*

A critical architectural consequence: your terminal emulator never interprets `ls` or `cd`. It sends keystrokes to a pseudoterminal (PTY), which forwards them to the shell, which executes them. Your terminal receives bytes back through the PTY and renders them. The terminal is an I/O device, not a command processor.

### 1.2 Why the Name "TTY"

The abbreviation TTY comes from **Teletype**, specifically the **Teletype Model 33 ASR** (Automatic Send-Receive), manufactured by the Teletype Corporation starting in 1963. The Model 33 was a printing terminal--an electromechanical device with a keyboard and a paper roll. When you typed, it encoded characters as a sequence of electrical pulses (7-bit ASCII, which the Model 33 helped standardize) and transmitted them over a serial line. Incoming characters drove a print head that physically struck an inked ribbon against paper.

The UNIX operating system, developed at Bell Labs starting in 1969, ran on PDP-7 and PDP-11 minicomputers. Ken Thompson and Dennis Ritchie connected Teletype Model 33 terminals to these machines via serial lines. In the kernel, each serial port was represented as a device file: `/dev/tty00`, `/dev/tty01`, etc. The abbreviation "tty" became the generic UNIX term for any terminal device.

When physical terminals were replaced by software emulators, the naming convention persisted. Today, `tty` in a UNIX-like system means "the terminal device associated with a process," even though no Teletype hardware exists.

### 1.3 /dev/tty on Modern Systems

On modern Linux and macOS systems, the TTY subsystem is a kernel facility:

| Device Path | Description |
|---|---|
| `/dev/tty` | The controlling terminal of the current process. Always refers to your own terminal, regardless of which one it is. |
| `/dev/tty0` | The currently active virtual console (Linux). |
| `/dev/tty1` - `/dev/tty63` | Virtual consoles (Linux kernel built-in terminals). Ctrl+Alt+F1-F6 switch between them. |
| `/dev/pts/0`, `/dev/pts/1`, ... | Pseudoterminal slave devices. Each terminal emulator window creates one. |
| `/dev/ptmx` | Pseudoterminal master multiplexer. Opening it allocates a new PTY pair. |
| `/dev/console` | The system console. Kernel messages go here. |

You can inspect your current TTY:

```bash
$ tty
/dev/pts/3

$ ls -la /dev/pts/
total 0
drwxr-xr-x  2 root root      0 Mar 24 08:00 .
crw-rw-rw-  1 root tty  136, 0 Mar 24 12:34 0
crw--w----  1 umit tty  136, 1 Mar 24 11:00 1
crw--w----  1 umit tty  136, 2 Mar 24 11:05 2
crw--w----  1 umit tty  136, 3 Mar 24 12:34 3
c---------  1 root root   5, 2 Mar 24 08:00 ptmx

$ ps -o tty,pid,comm
TT       PID COMM
pts/3  12345 zsh
pts/3  12400 vim
```

On macOS, the device paths differ slightly (`/dev/ttys000`, `/dev/ttys001`, etc.) but the semantics are identical. The kernel's TTY subsystem handles line discipline (echoing characters, handling Ctrl+C, converting CR to NL), buffering, and signal delivery--all inherited from the original Teletype interface.

### 1.4 Why Build Your Own Terminal?

If excellent terminal emulators already exist, why build one? There are four compelling reasons:

**1. Deep systems understanding.** A terminal emulator sits at the intersection of operating system kernel APIs (PTY, process management, signals), text rendering (font rasterization, Unicode, GPU shaders), input handling (keyboard encoding, mouse protocols, IME), and protocol parsing (VT100/xterm escape sequences). Building one teaches you things no tutorial will.

**2. Customization beyond configuration.** Every terminal makes opinionated tradeoffs. Alacritty chose simplicity over features (no tabs, no splits). iTerm2 chose features over simplicity (enormous settings panel). Ghostty chose correctness over compatibility. If your needs do not align with any existing terminal's philosophy, building your own is the only option.

**3. Performance exploration.** Terminal rendering is a surprisingly demanding workload. A `cat` of a large file can produce millions of escape sequences per second. GPU-accelerated terminals can render at 2ms frame times. Building one lets you explore real-world performance optimization: SIMD parsing, zero-copy buffers, GPU batch rendering, damage tracking.

**4. It is tractable.** Unlike building a web browser (millions of lines of code, years of work), a functional terminal emulator can be built by one developer in weeks. A minimal PTY + VT100 parser + grid + renderer can be under 5,000 lines of code. A production-quality terminal is 20,000-100,000 lines--ambitious but achievable.

This book will take you from zero to a working terminal emulator with GPU rendering, correct Unicode handling, and cross-platform PTY support.

---

## Chapter 2: History -- From Teletype Model 33 to GPU Terminals (1960-2026)

Understanding terminal history is not academic nostalgia. Every design decision in modern terminals--from the 80x24 default grid size to the specific byte sequences that change text color--traces directly back to physical hardware constraints from the 1960s and 1970s. If you do not understand the history, you will not understand why the protocols work the way they do.

![Terminal History Timeline](assets/06-terminal-history-timeline.svg)

### 2.1 Electromechanical Era (1837-1960s)

The story begins with telegraphy, not computing.

**1837-1844: Morse Telegraph.** Samuel Morse and Alfred Vail developed the telegraph and Morse code. The key insight: encode human language as electrical pulses over a wire. Morse code used variable-length encoding (E = single dot, Q = dash-dash-dot-dash), which was efficient for human operators but terrible for machines. The telegraph established the fundamental paradigm: a keyboard device at one end, a display/printer at the other, connected by a communication channel. This is exactly the architecture of a terminal emulator, 190 years later.

**1870-1874: Baudot Code.** Emile Baudot invented a fixed-length 5-bit character encoding and a mechanical multiplexing system that allowed multiple telegraph messages on one wire. The 5-bit encoding gave 32 possible characters--not enough for letters, digits, and punctuation, so Baudot used a "shift" mechanism: a LETTERS shift code switched the interpretation of subsequent codes to alphabetic, and a FIGURES shift code switched to numeric/punctuation. This shift mechanism is the ancestor of terminal "modes"--insert mode vs replace mode, application cursor keys mode, and so on. The unit "baud" (symbols per second) is named after Baudot.

**1908-1930s: Teletype machines.** Charles Krum and his son Howard developed the teleprinter (teletype) at the Morkrum Company (later Teletype Corporation, acquired by AT&T/Western Electric). These were electromechanical devices: a keyboard encoded characters into electrical signals, and a printer mechanism decoded incoming signals into printed characters on paper. The communication was full-duplex--you could type while receiving. Teletype machines replaced human Morse operators in commercial telegraphy and evolved into the dominant data terminal technology.

**1963: Teletype Model 33 ASR.** This is the single most important device in terminal history. The Model 33 ASR (Automatic Send-Receive) established conventions that persist to this day:

| Feature | Model 33 Specification | Modern Legacy |
|---|---|---|
| Character encoding | 7-bit ASCII (the Model 33 was the reference implementation for ASA X3.4-1963) | ASCII is the foundation of UTF-8, which is backward-compatible |
| Speed | 110 baud (approximately 10 characters per second) | The default baud rate in many serial configurations |
| Line ending | CR+LF (two separate operations) | Windows still uses CR+LF; UNIX uses LF only; HTTP uses CR+LF |
| BEL character (0x07) | Rang a physical bell on the machine | Terminal emulators play a sound or flash the screen |
| DEL character (0x7F) | Punched all 7 holes on paper tape (obliterated the previous character) | DEL is still 0x7F; Backspace is 0x08 |
| Columns | 72 characters per line (paper width) | Evolved to 80 columns (IBM punch cards), then the VT100's 80x24 |
| Paper tape | ASR model included paper tape reader/punch | No direct legacy, but the concept of "raw" vs "cooked" mode relates to buffering |

**CR+LF: The Physical Origin.** On the Model 33, "carriage return" (CR, 0x0D) physically moved the print head back to the left margin. "Line feed" (LF, 0x0A) physically advanced the paper by one line. These were two separate mechanical operations that took time--you could not combine them. When UNIX was developed, the kernel's TTY driver was designed to translate CR into LF (or CR+LF into LF) automatically, so programs only needed to handle LF. Windows preserved the original CR+LF convention. This mechanical legacy is why we still argue about line endings in 2026.

**BEL: The Actual Bell.** ASCII 0x07 (BEL) triggered an electromechanical bell on the Model 33--a real, physical bell that rang. In your terminal emulator, you need to handle this character. Options include playing a system sound, flashing the window (visual bell), bouncing the dock icon, or ignoring it. The most common modern behavior is a visual bell or system notification.

**DEL: Punch All Holes.** The DEL character (0x7F, binary 1111111) exists because of paper tape. Paper tape stored data as holes punched in specific positions. To "delete" a character on paper tape, you punched all seven holes, obliterating whatever was there before. This is why DEL is 0x7F (all bits set) rather than 0x00. In your terminal emulator, you will encounter both DEL (0x7F) and Backspace (0x08) and must handle them correctly depending on the terminal mode.

### 2.2 Hardware Video Terminals (1970s-1980s)

The transition from paper to screen was revolutionary. Instead of printing characters on paper (irreversible, slow, wasteful), a video terminal displayed characters on a CRT (cathode ray tube) screen. Characters could be overwritten, the cursor could move in two dimensions, and the display could be cleared instantly.

**1970: Datapoint 3300.** One of the earliest video display terminals. It displayed 12 lines of 72 or 80 characters. It had no cursor addressing--you could only append characters sequentially, like a teletype. This is sometimes called a "glass TTY" because it behaved like a teletype but used a screen instead of paper.

**1974: DEC VT52.** Digital Equipment Corporation's VT52 was the first widely-used terminal with **escape sequences**--special byte sequences that controlled cursor position, screen clearing, and other display attributes. The VT52 used a simple escape code format:

```
ESC A    — Cursor up
ESC B    — Cursor down
ESC C    — Cursor right
ESC D    — Cursor left
ESC H    — Cursor home (0,0)
ESC J    — Erase to end of screen
ESC K    — Erase to end of line
ESC Y r c — Direct cursor address (row, column as bytes + 31)
```

The VT52's escape sequences were proprietary to DEC, but they established the paradigm: in-band signaling where control commands are interleaved with printable text in the same byte stream. Your terminal parser must distinguish between printable characters (display them) and escape sequences (execute the command). This is the fundamental parsing problem in any terminal emulator.

**1978: DEC VT100.** The most important terminal ever made. The VT100 implemented **ANSI X3.64** (later ECMA-48/ISO 6429), a standardized escape sequence format that every terminal emulator still supports. Key specifications:

| Feature | VT100 Specification |
|---|---|
| Display | 80 columns x 24 rows (or 132 columns in wide mode) |
| Character set | ASCII + DEC Special Graphics (line-drawing characters) |
| Escape sequences | ANSI X3.64 CSI format: `ESC [ parameters command` |
| Attributes | Bold, underline, blink, reverse video |
| Scroll regions | Configurable top/bottom scroll margins |
| Auto-wrap | Configurable line wrapping at column 80 |
| Keyboard | Sends standard ASCII plus application-mode sequences |
| Processor | Intel 8080, 4KB ROM, 3KB RAM |

The VT100's 80x24 display became the de facto standard terminal size. This is why:
- The default terminal window in every emulator is 80x24.
- Many command-line tools assume 80 columns (man pages, help text formatting).
- SSH negotiation includes terminal dimensions, defaulting to 80x24.

The VT100 sold hundreds of thousands of units and became so dominant that "VT100 compatible" became a requirement for all subsequent terminals. When you build a terminal emulator, you are building a VT100 emulator with extensions. The CSI (Control Sequence Introducer) format `ESC [` is the foundation of your escape sequence parser.

**1983: DEC VT220.** Extended the VT100 with 8-bit character support (ISO 8859-1), user-defined keys, national replacement character sets, and additional control sequences. The VT220 introduced 8-bit control codes (C1 controls): instead of the 2-byte sequence `ESC [`, a single byte 0x9B (CSI) could be used. In practice, 8-bit controls are rarely used because they conflict with UTF-8 encoding. Your parser should support them but will encounter them infrequently.

**1987: DEC VT320 and VT420.** Further extensions: multiple pages (VT320), rectangular area operations, left/right margins (VT420). The VT420's rectangular operations (DECCRA: copy rectangular area, DECFRA: fill rectangular area) are advanced features that some modern terminals support for performance. You can defer these to a later implementation phase.

### 2.3 Software Emulators (1984-2010s)

With the rise of graphical operating systems, physical terminals were replaced by software emulators running in a window.

**1984: xterm.** The original X Window System terminal emulator, written by Mark Vandevoorde and later maintained by Thomas Dickey (who has maintained it for over 25 years). xterm is the reference implementation for terminal escape sequences. When documentation says "xterm extension," it means a sequence that xterm pioneered beyond the original VT100/VT220 standards. Key xterm contributions:

- 256-color support (SGR 38;5;N and 48;5;N)
- 24-bit true color (SGR 38;2;R;G;B and 48;2;R;G;B)
- Mouse tracking protocols (X10, normal, button, any-event)
- Window manipulation sequences (resize, iconify, move)
- OSC sequences for window title, clipboard access, hyperlinks
- Alternate screen buffer (ESC[?1049h/l)

Thomas Dickey's xterm control sequences document (colloquially "ctlseqs") at `https://invisible-island.net/xterm/ctlseqs/ctlseqs.html` is the single most important reference for terminal emulator developers. Bookmark it now.

**1990s-2000s: The proliferation.** As graphical desktops matured, many terminal emulators appeared:

| Terminal | Year | Platform | Technology | Notable Feature |
|---|---|---|---|---|
| rxvt | 1990 | X11 | C, Xlib | Lightweight xterm alternative |
| GNOME Terminal | 1999 | Linux | C, VTE/GTK | Integrated with GNOME desktop |
| Konsole | 1999 | Linux | C++, Qt | KDE integration, profiles |
| PuTTY | 1999 | Windows | C, Win32 | SSH client, became the standard Windows SSH terminal |
| Terminal.app | 2001 | macOS | Obj-C, Cocoa | macOS built-in terminal |
| iTerm | 2002 | macOS | Obj-C, Cocoa | Split panes, search, configurability |
| urxvt (rxvt-unicode) | 2003 | X11 | C, Xlib | Unicode support, Perl extensions, daemon mode |
| iTerm2 | 2010 | macOS | Obj-C/Swift, Cocoa | Major rewrite, became macOS standard for developers |

This era was characterized by CPU-based rendering. Text was drawn using the platform's 2D graphics APIs: Xft/Xrender on X11, Quartz/CoreText on macOS, GDI on Windows. These renderers were correct and featureful but had performance ceilings. Drawing thousands of characters per frame using CPU-based text APIs was slow, especially with complex Unicode, color schemes, and transparency.

**VTE (Virtual Terminal Emulator) library** deserves special mention. VTE is a GTK widget that implements a terminal emulator--used by GNOME Terminal, Tilix, Terminator, and many others. If you are building a GTK-based terminal, VTE does 90% of the work. However, VTE's architecture (C, single-threaded rendering, CPU-based) limits its performance. Understanding its limitations motivates the GPU revolution.

### 2.4 GPU Revolution (2016-2026)

The key insight: terminal rendering is fundamentally a batch rendering problem. A terminal with 200 columns and 50 rows has 10,000 cells. Each cell is a textured rectangle with a foreground color, background color, and potentially a glyph. This is exactly the kind of workload GPUs excel at--drawing thousands of small, independent quads with texture sampling.

**2016: Alacritty** (Rust + OpenGL). Joe Wilm created Alacritty as "the fastest terminal emulator in existence," and it proved the concept. By rendering the terminal grid as textured quads on the GPU using OpenGL, Alacritty achieved dramatically lower latency and higher throughput than CPU-rendered terminals. Key architectural decisions:

- Written in Rust for memory safety and performance
- OpenGL 3.3 for rendering (widely supported)
- Pre-rasterized glyph atlas (FreeType + fontconfig)
- Zero configuration philosophy (later added TOML config)
- No tabs, no splits (delegated to tmux/window manager)
- ~25,000 lines of Rust code (core)

Alacritty's source code is the best study material for understanding GPU terminal rendering. The `alacritty_terminal` crate (parser, grid, terminal state) is cleanly separated from the renderer, making it reusable.

GitHub: `https://github.com/alacritty/alacritty` -- 57K+ stars.

**2018: Kitty** (C + OpenGL). Kovid Goyal's Kitty took the GPU approach further with the "Kitty Graphics Protocol"--a standard for displaying inline images and animations in the terminal. Kitty also pioneered:

- Custom keyboard encoding protocol (disambiguates key press vs release, modifier combinations)
- Ligature rendering (programming font ligatures)
- GPU-based font rasterization
- Multiple rendering backends

The Kitty keyboard protocol is gaining wide adoption and may become the de facto standard, replacing the ambiguous legacy keyboard encoding. If you are building a new terminal, implementing the Kitty keyboard protocol is strongly recommended.

GitHub: `https://github.com/kovidgoyal/kitty` -- 25K+ stars.

**2019: Windows Terminal** (C++ + DirectX/DXGI). Microsoft's open-source terminal for Windows, replacing the ancient `conhost.exe`. It introduced the **ConPTY** (Console Pseudoterminal) API, which finally gave Windows a proper PTY abstraction similar to UNIX. Windows Terminal uses DirectWrite for text shaping and a custom Atlas-based renderer backed by DirectX 11 (later moving to a DirectX 12 backend).

GitHub: `https://github.com/microsoft/terminal` -- 96K+ stars.

Windows Terminal is significant because it legitimized terminal development on Windows and provided the ConPTY API that third-party terminals (Alacritty, WezTerm, Ghostty) use for Windows support.

**2020: WezTerm** (Rust + OpenGL/Metal/Vulkan). Wez Furlong created a feature-rich, cross-platform terminal in Rust with a Lua configuration system, built-in multiplexer (no tmux needed), and multiple GPU backends. WezTerm is notable for its correctness--it passes more terminal conformance tests than most other modern terminals.

**2023: Warp** (Rust + Metal). Warp re-imagined the terminal as a modern application with AI integration, block-based command output, collaborative features, and a GUI that does not look like a traditional terminal. It challenged the assumption that a terminal must be a character grid. Warp is controversial among traditional terminal users but commercially successful.

**2024: Ghostty** (Zig + Metal/OpenGL/Vulkan). Mitchell Hashimoto (founder of HashiCorp) created Ghostty with a focus on correctness, performance, and native platform integration. Key characteristics:

- Written in Zig (manual memory management, no GC, comptime metaprogramming)
- Native Metal renderer on macOS, with OpenGL and Vulkan backends for Linux
- ~2ms frame latency (measured input-to-display)
- libghostty: the terminal emulation core as a reusable C-ABI library
- Uses a custom VT parser derived from systematic ECMA-48 analysis
- Native macOS app (AppKit, not Electron or cross-platform GUI)

Ghostty's architecture--separating the terminal core (`libghostty`) from the platform-specific GUI--is the recommended approach for this book. It maximizes code reuse and testability.

GitHub: `https://github.com/ghostty-org/ghostty` -- 48K+ stars.

**2025: Rio** (Rust + WebGPU/wgpu). Rio uses the `wgpu` library, which provides a WebGPU API that maps to Metal, Vulkan, DirectX 12, or OpenGL automatically. This achieves cross-platform GPU rendering with a single codebase, avoiding the need for per-platform render backends. Rio represents the cutting edge of cross-platform GPU terminal development.

**Summary: The GPU Terminal Landscape (2026)**

| Terminal | Language | GPU API | Lines of Code (approx.) | Key Differentiator |
|---|---|---|---|---|
| Alacritty | Rust | OpenGL 3.3 | ~30K | Minimalism, speed |
| Kitty | C/Python | OpenGL | ~60K | Graphics protocol, extensibility |
| Windows Terminal | C++ | DirectX 11/12 | ~150K | Windows native, ConPTY |
| WezTerm | Rust | OpenGL/Metal/Vulkan | ~100K | Feature completeness, Lua config |
| Ghostty | Zig | Metal/OpenGL/Vulkan | ~80K | Correctness, native UI, libghostty |
| Rio | Rust | wgpu (WebGPU) | ~25K | Cross-platform GPU via wgpu |

---

## Chapter 3: Architecture Overview -- The 5 Building Blocks

Every terminal emulator, regardless of implementation language or rendering technology, consists of the same five fundamental components. Understanding this architecture is essential before diving into implementation.

![Terminal Architecture](assets/01-terminal-architecture.svg)

### 3.1 The Five Layers

```
                    +---------------------+
                    |    User / Display   |    Layer 5: The screen you see
                    +---------------------+
                              |
                    +---------------------+
                    |      Renderer       |    Layer 4: GPU/CPU drawing
                    +---------------------+
                              |
                    +---------------------+
                    |   Terminal Core     |    Layer 3: Parser + Grid State
                    |  (Parser + Grid)    |
                    +---------------------+
                              |
                    +---------------------+
                    |        PTY          |    Layer 2: Kernel pseudoterminal
                    +---------------------+
                              |
                    +---------------------+
                    |   Input Handler     |    Layer 1: Keyboard/mouse encoding
                    +---------------------+
```

**Layer 1: Input Handler.** Translates physical keyboard events and mouse events into byte sequences that the shell and programs understand. When you press the letter `a`, the input handler sends the byte `0x61`. When you press `Ctrl+C`, it sends `0x03` (ETX). When you press an arrow key, it sends an escape sequence like `ESC [ A` (or `ESC O A` in application mode). The input handler must also manage:

- Keyboard encoding (legacy vs Kitty protocol vs fixterms)
- Mouse encoding (X10, SGR, urxvt pixel mode)
- Input Method Editor (IME) for CJK languages
- Clipboard paste (bracketed paste mode: ESC[200~ ... ESC[201~)
- Key repeat, dead keys, compose sequences

**Layer 2: PTY (Pseudoterminal).** The bridge between your terminal emulator (user-space application) and the shell process (another user-space application), mediated by the kernel. The PTY is a pair of file descriptors: the master side (held by your terminal) and the slave side (attached to the shell's stdin/stdout/stderr). When your terminal writes bytes to the master, they appear on the shell's stdin. When the shell writes to stdout, the bytes appear on the master for your terminal to read. The kernel's line discipline layer sits in between, handling echo, signals (Ctrl+C to SIGINT), and canonical-mode line editing.

**Layer 3: Terminal Core (Parser + Grid).** The brain of the terminal emulator. This layer:
1. **Parses** the incoming byte stream from the PTY, identifying printable characters, control characters, and escape sequences.
2. **Executes** escape sequence commands: moving the cursor, changing colors, scrolling regions, switching modes.
3. **Updates** the character grid: a 2D array of cells, each containing a character, foreground color, background color, and attribute flags.
4. **Manages** terminal state: cursor position, scroll region, character set, tab stops, mode flags (insert mode, auto-wrap, origin mode, etc.).

This layer is pure logic--no I/O, no rendering. It takes bytes in and updates a grid data structure. This makes it highly testable and reusable. Alacritty's `alacritty_terminal` crate, Ghostty's `libghostty`, and WezTerm's `termwiz` are all implementations of this layer as standalone libraries.

**Layer 4: Renderer.** Reads the character grid from Layer 3 and draws it to the screen. This is where GPU vs CPU rendering matters. The renderer must:
1. Rasterize glyphs (turn font outlines into pixels) and cache them in a glyph atlas.
2. Shape text (handle ligatures, combining characters, bidirectional text) using HarfBuzz or CoreText.
3. Build a batch of quads (one per character cell) with texture coordinates pointing into the glyph atlas.
4. Submit the batch to the GPU (or draw with CPU-based 2D graphics).
5. Handle damage tracking: only re-render cells that changed since the last frame.
6. Manage the cursor, selection highlighting, and search highlighting.
7. Handle window resize: recalculate the grid dimensions, inform the PTY via TIOCSWINSZ.

**Layer 5: Display (Windowing).** The platform-specific windowing layer that provides a surface to render onto, delivers keyboard/mouse events, and manages the window lifecycle. On Linux, this is X11 (via Xlib or XCB) or Wayland. On macOS, this is AppKit (NSWindow, NSView) or SwiftUI. On Windows, this is Win32 (HWND) or UWP. Cross-platform libraries like `winit` (Rust) or GLFW (C) abstract this layer.

### 3.2 Data Flow

A complete round-trip through the terminal looks like this:

**Keystroke to display:**

```
1. User presses 'l' key
2. OS delivers key event to your window
3. Input Handler encodes it as byte 0x6C
4. Terminal writes 0x6C to PTY master fd
5. Kernel line discipline: if echo mode is on, sends 0x6C back to master
   Kernel line discipline: forwards 0x6C to PTY slave fd
6. Shell reads 0x6C from stdin, displays it in the prompt
   (Shell writes rendered prompt back to stdout/PTY slave)
7. Terminal reads echoed/output bytes from PTY master fd
8. Parser processes bytes: 0x6C is printable, insert 'l' at cursor position
9. Grid cell at cursor position updated: character='l', fg=default, bg=default
10. Cursor advances one column to the right
11. Renderer detects the changed cell (damage tracking)
12. Renderer draws the glyph for 'l' at the cell's position
13. Frame is presented to the display
```

**Command output:**

```
1. User presses Enter (Input Handler sends 0x0D)
2. Kernel line discipline converts CR to NL, sends to shell
3. Shell executes the command (e.g., "ls")
4. "ls" writes filenames to stdout, which goes to PTY slave
5. Kernel forwards bytes to PTY master
6. Terminal reads bytes, Parser processes them
7. Output may contain escape sequences (e.g., colored filenames)
8. Parser updates grid cells with characters and color attributes
9. Renderer draws the entire changed region
```

### 3.3 Kernel-Space vs User-Space

The terminal architecture spans two privilege domains:

**User-space** (your code): The terminal emulator process and the shell process both run in user-space. They have no direct access to hardware or kernel data structures. They communicate through file descriptors (the PTY) and system calls.

**Kernel-space** (the PTY layer): The PTY device driver and the line discipline live in the kernel. When your terminal writes to the PTY master file descriptor, the `write()` system call traps into the kernel. The kernel's TTY subsystem processes the bytes through the line discipline (handling echo, signals, canonical mode) and makes them available on the slave side. Similarly, when the shell writes to the slave, the kernel makes bytes available on the master.

This kernel mediation is why terminal behavior can seem magical. When you press Ctrl+C and the foreground process dies, that is the kernel's line discipline recognizing the INTR character (default: 0x03), generating a SIGINT signal, and delivering it to the foreground process group. Your terminal emulator does not need to implement this--the kernel does it.

However, your terminal does need to:
- Configure the line discipline (raw mode vs canonical mode) via `tcsetattr()`.
- Set the window size via `ioctl(fd, TIOCSWINSZ, &ws)` so programs know the terminal dimensions.
- Handle `SIGWINCH` to detect when the window is resized.
- Handle `SIGCHLD` to detect when the shell process exits.

### 3.4 Concurrency Model

A terminal emulator is inherently concurrent. At minimum, you need:

1. **A thread (or async task) reading from the PTY.** The shell can produce output at any time, and you must read it promptly to avoid filling the PTY buffer (which blocks the shell).

2. **A thread (or async task) handling input events.** Keyboard and mouse events from the windowing system must be processed and written to the PTY.

3. **A render loop.** The renderer runs on the main thread (required by most GPU APIs and windowing systems) and draws frames either on a timer (e.g., 60 FPS) or on demand when the grid changes.

The most common architecture:

```
+------------------+     +------------------+     +------------------+
|  PTY Reader      |     |  Main Thread     |     |  Event Loop      |
|  (thread/async)  |---->|  (render loop)   |<----|  (OS events)     |
|  reads bytes,    |     |  parser, grid,   |     |  keyboard, mouse |
|  wakes renderer  |     |  renderer        |     |  resize, focus   |
+------------------+     +------------------+     +------------------+
```

In Rust, this is often implemented with channels (`crossbeam`, `flume`) or `mio`/`tokio` for async I/O. In Zig, it is manual threading with `std.Thread` and atomics. In C++, it is typically `std::thread` with a lock-free queue or condition variable.

The synchronization point is the terminal grid. The PTY reader produces parsed data that updates the grid; the renderer reads the grid to draw frames. You need either:
- A mutex protecting the grid (simple, potential contention).
- A double-buffered grid (PTY writer builds the back buffer, renderer reads the front buffer, swap atomically).
- A lock-free queue of grid diffs (complex but highest throughput).

Alacritty uses a mutex (`Arc<FairMutex<Term>>`). Ghostty uses a more sophisticated approach with a dedicated terminal thread. For your first implementation, a mutex is the right choice.

---

# PART II: DEEP DIVE -- CORE COMPONENTS

---

## Chapter 4: PTY -- Talking to the Shell

The pseudoterminal (PTY) is the kernel facility that connects your terminal emulator to the shell. Without it, you are just drawing characters in a window with no program to talk to. This chapter covers the PTY API in depth for Linux, macOS, Windows, and iOS.

![PTY Communication Flow](assets/02-pty-communication-flow.svg)

### 4.1 Linux PTY

On Linux, the PTY subsystem provides a pair of virtual character devices: a **master** and a **slave**. The master is held by the terminal emulator. The slave is connected to the shell process's stdin, stdout, and stderr. Between them sits the kernel's **line discipline**, which handles character echoing, signal generation (Ctrl+C to SIGINT), and canonical mode line editing.

#### 4.1.1 The Device Files

| Path | Description |
|---|---|
| `/dev/ptmx` | PTY master multiplexer. `open("/dev/ptmx", O_RDWR)` allocates a new PTY pair and returns the master fd. |
| `/dev/pts/N` | PTY slave devices. Each `open("/dev/ptmx")` creates a new `/dev/pts/N` entry (N = 0, 1, 2, ...). |
| `/dev/pts/ptmx` | Devpts-specific multiplexer (used with mount namespaces/containers). |

#### 4.1.2 The Low-Level API

The POSIX standard defines the following functions for PTY allocation:

```c
#include <stdlib.h>
#include <fcntl.h>

// Step 1: Open the master side
int master_fd = posix_openpt(O_RDWR | O_NOCTTY);
if (master_fd == -1) { perror("posix_openpt"); exit(1); }

// Step 2: Grant access to the slave device
// Sets ownership and permissions on the slave device file
if (grantpt(master_fd) == -1) { perror("grantpt"); exit(1); }

// Step 3: Unlock the slave device
// Allows the slave to be opened
if (unlockpt(master_fd) == -1) { perror("unlockpt"); exit(1); }

// Step 4: Get the slave device path
char *slave_name = ptsname(master_fd);
if (slave_name == NULL) { perror("ptsname"); exit(1); }
// slave_name is something like "/dev/pts/3"

// Step 5: Open the slave side
int slave_fd = open(slave_name, O_RDWR | O_NOCTTY);
if (slave_fd == -1) { perror("open slave"); exit(1); }
```

`posix_openpt()` is the POSIX-standard way to allocate a PTY. On Linux, it is equivalent to `open("/dev/ptmx", flags)`. The `O_NOCTTY` flag prevents the master from becoming the controlling terminal of the calling process.

`grantpt()` changes the ownership of the slave device to the calling user and sets its permissions to 0620 (owner read/write, group write for the `tty` group). On modern Linux with devpts mounted with the `gid=5,mode=0620` option, this is often a no-op but must still be called.

`unlockpt()` unlocks the slave side so it can be opened. A newly allocated PTY starts locked.

`ptsname()` returns the path of the slave device. **Warning**: `ptsname()` returns a pointer to a static buffer and is not thread-safe. Use `ptsname_r()` (GNU extension) for thread safety.

#### 4.1.3 The Convenient API: forkpty()

For most terminal emulators, `forkpty()` is the right function. It combines PTY allocation, forking, and slave setup in one call:

```c
#include <pty.h>      // Linux
#include <util.h>     // macOS (also <pty.h> on some versions)
#include <utmp.h>
#include <unistd.h>
#include <sys/wait.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <poll.h>

int main(void) {
    int master_fd;
    pid_t pid;

    // Set desired window size
    struct winsize ws = {
        .ws_row = 24,
        .ws_col = 80,
        .ws_xpixel = 0,  // pixel width (optional, used by some programs)
        .ws_ypixel = 0,  // pixel height (optional)
    };

    // forkpty() does ALL of the following:
    // 1. Calls posix_openpt() to allocate a PTY
    // 2. Calls grantpt() and unlockpt()
    // 3. Calls fork()
    // 4. In the child:
    //    a. Creates a new session (setsid())
    //    b. Opens the slave device
    //    c. Makes the slave the controlling terminal (TIOCSCTTY)
    //    d. Duplicates the slave fd to stdin, stdout, stderr (dup2)
    //    e. Closes the master fd and the original slave fd
    // 5. Sets the window size (TIOCSWINSZ) if ws is non-NULL
    pid = forkpty(&master_fd, NULL, NULL, &ws);

    if (pid == -1) {
        perror("forkpty");
        exit(1);
    }

    if (pid == 0) {
        // *** CHILD PROCESS ***
        // We are now running with stdin/stdout/stderr connected to the PTY slave.
        // The shell will inherit these file descriptors.

        // Set the TERM environment variable so programs know our capabilities
        setenv("TERM", "xterm-256color", 1);

        // Optional: set COLORTERM for true color support
        setenv("COLORTERM", "truecolor", 1);

        // Execute the user's shell
        char *shell = getenv("SHELL");
        if (shell == NULL) shell = "/bin/sh";

        // Use execlp to replace the child process with the shell
        // The "-" prefix makes it a login shell
        char login_shell[256];
        snprintf(login_shell, sizeof(login_shell), "-%s",
                 strrchr(shell, '/') ? strrchr(shell, '/') + 1 : shell);

        execlp(shell, login_shell, (char *)NULL);

        // If execlp returns, it failed
        perror("execlp");
        _exit(127);
    }

    // *** PARENT PROCESS (terminal emulator) ***
    // master_fd is our end of the PTY.
    // Writing to master_fd sends data to the shell's stdin.
    // Reading from master_fd receives data from the shell's stdout/stderr.

    // Set master to non-blocking mode for async I/O
    int flags = fcntl(master_fd, F_GETFL);
    fcntl(master_fd, F_SETFL, flags | O_NONBLOCK);

    // Main loop: forward stdin to master, master to stdout
    // (In a real terminal, this would be the event loop)
    struct pollfd fds[2] = {
        { .fd = STDIN_FILENO, .events = POLLIN },
        { .fd = master_fd,    .events = POLLIN },
    };

    // Put our own terminal in raw mode so keystrokes pass through immediately
    struct termios original_termios, raw_termios;
    tcgetattr(STDIN_FILENO, &original_termios);
    raw_termios = original_termios;
    cfmakeraw(&raw_termios);
    tcsetattr(STDIN_FILENO, TCSANOW, &raw_termios);

    char buf[4096];
    int running = 1;

    while (running) {
        int ret = poll(fds, 2, -1);
        if (ret == -1) {
            if (errno == EINTR) continue;
            break;
        }

        // Data from our stdin -> PTY master (to shell)
        if (fds[0].revents & POLLIN) {
            ssize_t n = read(STDIN_FILENO, buf, sizeof(buf));
            if (n > 0) {
                write(master_fd, buf, n);
            } else if (n == 0) {
                running = 0;
            }
        }

        // Data from PTY master (from shell) -> our stdout
        if (fds[1].revents & POLLIN) {
            ssize_t n = read(master_fd, buf, sizeof(buf));
            if (n > 0) {
                write(STDOUT_FILENO, buf, n);
            } else if (n == 0) {
                running = 0;
            }
        }

        // Check if shell exited
        if (fds[1].revents & (POLLHUP | POLLERR)) {
            running = 0;
        }
    }

    // Restore terminal settings
    tcsetattr(STDIN_FILENO, TCSANOW, &original_termios);

    // Wait for child to finish
    int status;
    waitpid(pid, &status, 0);

    if (WIFEXITED(status)) {
        printf("\nShell exited with status %d\n", WEXITSTATUS(status));
    }

    close(master_fd);
    return 0;
}
```

Compile and run:

```bash
gcc -o miniterm miniterm.c -lutil
./miniterm
```

This is a complete, minimal terminal emulator. It forwards bytes between your real terminal and a shell running in a PTY. It does not parse escape sequences or render anything--it delegates rendering to your outer terminal. But it demonstrates the full PTY lifecycle.

#### 4.1.4 Line Discipline

The line discipline is the kernel layer between the master and slave sides of the PTY. It processes bytes flowing in both directions:

**Canonical mode (cooked mode):** The default. The line discipline buffers input until Enter is pressed, supports basic line editing (Backspace to delete, Ctrl+U to kill line), and echoes typed characters back to the master. Programs like `cat` and `read` in shell scripts use canonical mode.

**Raw mode:** No processing. Every byte written to the master appears immediately on the slave, and vice versa. No echo, no signals, no line editing. Programs like `vim`, `less`, and `top` set raw mode because they handle all input processing themselves. Your terminal emulator should set the PTY's terminal attributes to raw mode on the terminal emulator side (your stdin, if you are wrapping another terminal) but leave the PTY slave in its default state so the shell and programs can set whatever mode they need.

**Key line discipline behaviors:**

| Input | Canonical Mode Behavior | Raw Mode Behavior |
|---|---|---|
| Ctrl+C (0x03) | Generates SIGINT to foreground process group | Byte 0x03 passed through |
| Ctrl+Z (0x1A) | Generates SIGTSTP (suspend) | Byte 0x1A passed through |
| Ctrl+D (0x04) | EOF if input buffer is empty; deletes char otherwise | Byte 0x04 passed through |
| Ctrl+\ (0x1C) | Generates SIGQUIT (core dump) | Byte 0x1C passed through |
| Ctrl+S (0x13) | XOFF -- stop output (flow control) | Byte 0x13 passed through |
| Ctrl+Q (0x11) | XON -- resume output | Byte 0x11 passed through |
| Backspace | Deletes previous character from buffer, echoes erase sequence | Byte 0x7F passed through |
| Enter (CR, 0x0D) | Translates to NL (0x0A), sends buffered line to slave | Byte 0x0D passed through |

The line discipline is configured via `struct termios` and the `tcsetattr()` system call. Key flags:

```c
struct termios {
    tcflag_t c_iflag;   // Input flags (ICRNL, IXON, ISTRIP, ...)
    tcflag_t c_oflag;   // Output flags (OPOST, ONLCR, ...)
    tcflag_t c_cflag;   // Control flags (CSIZE, PARENB, ...)
    tcflag_t c_lflag;   // Local flags (ECHO, ICANON, ISIG, ...)
    cc_t c_cc[NCCS];    // Special characters (VINTR, VEOF, VERASE, ...)
};
```

| Flag | Field | Effect When Set |
|---|---|---|
| `ECHO` | `c_lflag` | Echo input characters back to master |
| `ICANON` | `c_lflag` | Canonical mode (line buffering) |
| `ISIG` | `c_lflag` | Generate signals for Ctrl+C, Ctrl+Z, Ctrl+\ |
| `ICRNL` | `c_iflag` | Translate CR (0x0D) to NL (0x0A) on input |
| `ONLCR` | `c_oflag` | Translate NL to CR+NL on output |
| `OPOST` | `c_oflag` | Enable output processing |
| `IXON` | `c_iflag` | Enable XON/XOFF flow control |

For your terminal emulator, you generally do not touch the PTY slave's termios--the shell and programs running inside manage their own termios settings via `tcsetattr()` on their stdin (which is the slave fd).

#### 4.1.5 Resizing the PTY

When the user resizes the terminal window, you must inform the PTY of the new dimensions:

```c
#include <sys/ioctl.h>

void resize_pty(int master_fd, int rows, int cols, int xpixel, int ypixel) {
    struct winsize ws = {
        .ws_row = rows,
        .ws_col = cols,
        .ws_xpixel = xpixel,
        .ws_ypixel = ypixel,
    };

    if (ioctl(master_fd, TIOCSWINSZ, &ws) == -1) {
        perror("TIOCSWINSZ");
    }
    // The kernel automatically sends SIGWINCH to the foreground process group
    // Programs like vim, less, and top handle SIGWINCH to redraw.
}
```

The `TIOCSWINSZ` ioctl sets the window size on the PTY. The kernel then sends `SIGWINCH` to the foreground process group of the slave side. Programs that care about terminal dimensions (vim, less, top, tmux) handle this signal to redraw themselves. The `ws_xpixel` and `ws_ypixel` fields are used by some programs (e.g., Kitty's graphics protocol) to calculate pixel-accurate positioning.

### 4.2 macOS PTY

macOS uses the same POSIX PTY API as Linux, with BSD heritage. The APIs `posix_openpt()`, `grantpt()`, `unlockpt()`, `ptsname()`, and `forkpty()` all work identically. Key differences:

**Device paths:** macOS uses `/dev/ptmx` for allocation and `/dev/ttysNNN` for slave devices (e.g., `/dev/ttys000`, `/dev/ttys001`) instead of Linux's `/dev/pts/N`.

**Header files:** On macOS, `forkpty()` is declared in `<util.h>` (BSD heritage) rather than `<pty.h>` (GNU/Linux). Some macOS versions also provide `<pty.h>` as a compatibility shim. Use conditional compilation:

```c
#ifdef __APPLE__
    #include <util.h>
#else
    #include <pty.h>
#endif
```

**Linking:** On Linux, `forkpty()` requires linking with `-lutil`. On macOS, it is in `libSystem` (linked automatically).

**Sandbox considerations:** macOS apps distributed via the App Store or with the App Sandbox entitlement cannot use `forkpty()` directly. The sandbox restricts `posix_openpt()` and `fork()`. This is why most macOS terminal emulators (Alacritty, Ghostty, iTerm2) are distributed outside the App Store, or use a helper process that runs outside the sandbox. If you need App Store distribution, you must use XPC to communicate with a non-sandboxed helper binary.

**CoreFoundation / Grand Central Dispatch:** On macOS, you can use `dispatch_source_create(DISPATCH_SOURCE_TYPE_READ, master_fd, 0, queue)` instead of `poll()` or `select()` for event-driven PTY reading. This integrates cleanly with the macOS run loop:

```c
dispatch_source_t source = dispatch_source_create(
    DISPATCH_SOURCE_TYPE_READ,
    master_fd,
    0,
    dispatch_get_main_queue()
);

dispatch_source_set_event_handler(source, ^{
    char buf[4096];
    ssize_t n = read(master_fd, buf, sizeof(buf));
    if (n > 0) {
        // Process bytes: parse escape sequences, update grid
        process_pty_output(buf, n);
    }
});

dispatch_source_set_cancel_handler(source, ^{
    close(master_fd);
});

dispatch_resume(source);
```

### 4.3 Windows ConPTY

Windows has never had a UNIX-style PTY. For decades, the Win32 Console API was the only way to build console applications, and it was fundamentally different from UNIX terminals: instead of a byte stream with escape sequences, it used a structured API with function calls like `WriteConsoleOutput()` that wrote character cells directly to a screen buffer.

This changed in 2018 with the introduction of **ConPTY** (Console Pseudoterminal), part of the Windows 10 1809 update. ConPTY provides a UNIX-like PTY abstraction: a pair of pipes that carry VT100/xterm escape sequences, bridging the gap between UNIX-style terminal emulators and legacy Win32 console applications.

#### 4.3.1 The Legacy Console API

Before ConPTY, terminal emulators on Windows had two options:

1. **Use the Console API directly.** Create a console screen buffer, write characters to it using `WriteConsoleOutput()`, read input using `ReadConsoleInput()`. This was entirely different from UNIX terminals and did not support escape sequences at all.

2. **Use WinPTY.** An open-source library by Ryan Prichard that created a hidden console window, ran the child process in it, scraped the console screen buffer for changes, and translated them into VT escape sequences. This was a clever hack but inherently lossy and slow--it polled the screen buffer rather than receiving a byte stream.

#### 4.3.2 ConPTY API

ConPTY introduces `CreatePseudoConsole()`, which creates a pseudoconsole that translates between VT sequences and the Win32 Console API internally:

```cpp
#include <windows.h>
#include <process.h>
#include <stdio.h>

// Error handling macro
#define CHECK_HR(hr) if (FAILED(hr)) { printf("Error: 0x%08X\n", hr); return 1; }

int main() {
    HRESULT hr;

    // Step 1: Create pipes for communication
    // These replace the UNIX PTY master fd.
    HANDLE hPipeIn_Read, hPipeIn_Write;   // Terminal reads from hPipeIn_Read
    HANDLE hPipeOut_Read, hPipeOut_Write; // Terminal writes to hPipeOut_Write

    CreatePipe(&hPipeIn_Read, &hPipeIn_Write, NULL, 0);
    CreatePipe(&hPipeOut_Read, &hPipeOut_Write, NULL, 0);

    // Step 2: Create the pseudoconsole
    COORD size = { .X = 80, .Y = 24 };
    HPCON hPC;

    // hPipeOut_Read: ConPTY reads input from here (keystrokes from terminal)
    // hPipeIn_Write: ConPTY writes output here (shell output to terminal)
    hr = CreatePseudoConsole(size, hPipeOut_Read, hPipeIn_Write, 0, &hPC);
    CHECK_HR(hr);

    // Close the handles that ConPTY now owns
    CloseHandle(hPipeOut_Read);
    CloseHandle(hPipeIn_Write);

    // Step 3: Set up the child process with the pseudoconsole
    STARTUPINFOEXW si;
    ZeroMemory(&si, sizeof(si));
    si.StartupInfo.cb = sizeof(si);

    // Allocate attribute list for the pseudoconsole handle
    SIZE_T attrListSize = 0;
    InitializeProcThreadAttributeList(NULL, 1, 0, &attrListSize);
    si.lpAttributeList = (LPPROC_THREAD_ATTRIBUTE_LIST)malloc(attrListSize);
    InitializeProcThreadAttributeList(si.lpAttributeList, 1, 0, &attrListSize);

    // Associate the pseudoconsole with the child process
    UpdateProcThreadAttribute(
        si.lpAttributeList,
        0,
        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
        hPC,
        sizeof(HPCON),
        NULL, NULL
    );

    // Step 4: Create the child process (cmd.exe or powershell.exe)
    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    wchar_t cmd[] = L"cmd.exe";
    BOOL success = CreateProcessW(
        NULL,                        // Application name
        cmd,                         // Command line
        NULL, NULL,                  // Process/thread security attributes
        FALSE,                       // Inherit handles
        EXTENDED_STARTUPINFO_PRESENT, // Creation flags
        NULL,                        // Environment
        NULL,                        // Current directory
        &si.StartupInfo,             // Startup info
        &pi                          // Process info
    );

    if (!success) {
        printf("CreateProcess failed: %lu\n", GetLastError());
        return 1;
    }

    // Step 5: Communication loop
    // Read from hPipeIn_Read (shell output, VT sequences)
    // Write to hPipeOut_Write (keyboard input, VT sequences)

    // Example: Read output from the shell
    char buffer[4096];
    DWORD bytesRead;
    while (ReadFile(hPipeIn_Read, buffer, sizeof(buffer), &bytesRead, NULL)) {
        if (bytesRead == 0) break;
        // buffer now contains VT escape sequences from the shell
        // Parse them and update your terminal grid
        process_vt_output(buffer, bytesRead);
    }

    // Cleanup
    ClosePseudoConsole(hPC);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    DeleteProcThreadAttributeList(si.lpAttributeList);
    free(si.lpAttributeList);
    CloseHandle(hPipeIn_Read);
    CloseHandle(hPipeOut_Write);

    return 0;
}
```

**How ConPTY works internally:** ConPTY runs an internal VT parser/renderer. When a legacy Win32 console application calls `WriteConsoleOutput()` (structured API), ConPTY translates that into VT escape sequences and writes them to the output pipe. When the terminal writes VT sequences to the input pipe, ConPTY translates them into Console API input events. This bidirectional translation is why ConPTY can run both VT-aware programs (like WSL's bash) and legacy Win32 console programs (like `cmd.exe`) without the program knowing a PTY is involved.

**Resizing:** Use `ResizePseudoConsole(hPC, newSize)`:

```cpp
COORD newSize = { .X = 120, .Y = 40 };
hr = ResizePseudoConsole(hPC, newSize);
```

**WinPTY vs ConPTY:** WinPTY is still used as a fallback on Windows versions before 1809 (October 2018). If you need to support Windows 7/8, you must support WinPTY. For Windows 10 1809+, ConPTY is the correct choice.

### 4.4 iOS -- No PTY

iOS does not provide a PTY API. The iOS kernel does have the TTY subsystem (it is a Darwin/XNU kernel, the same as macOS), but apps are sandboxed and cannot access `/dev/ptmx` or create child processes with `fork()`. This makes building a traditional terminal emulator on iOS impossible. The workarounds are:

**SSH-based terminals.** The most common approach. Apps like **Blink Shell** and **Termius** connect to a remote server via SSH and run the shell there. The terminal emulation (parsing, rendering) happens locally on the iOS device, but the PTY and shell are on the remote machine. The communication channel is an SSH channel instead of a local PTY. From the terminal emulator's perspective, this changes only the I/O layer--you read/write an SSH channel instead of a file descriptor. The parser and renderer are identical.

**User-mode emulation.** **iSH** emulates an x86 Linux kernel entirely in user-space, implementing system calls including `fork()`, `exec()`, and the PTY subsystem. This works but is slow--iSH translates x86 instructions to ARM and emulates the Linux kernel in a single iOS process. It provides a genuine local shell experience at the cost of performance.

**WASM-based terminals.** **a-Shell** compiles command-line tools to WebAssembly and runs them in a WASM runtime on iOS. It provides a shell-like experience with `ls`, `python`, `vim`, etc., but the "shell" is a custom implementation, not bash or zsh. There is no real PTY--the WASM runtime communicates with the terminal display through an internal API.

**The bottom line:** If you are building a terminal for iOS, you will implement SSH as your transport layer instead of a local PTY. The rest of the terminal (parser, grid, renderer) is the same. Chapter 4's PTY code does not apply to iOS.

### 4.5 Code Examples

For complete, runnable code examples:

- **C PTY example (Linux/macOS):** See [examples/pty-fork-example.c](examples/pty-fork-example.c) -- the full `forkpty()` example from Section 4.1.3 with signal handling, error handling, and cleanup.
- **Python minimal terminal:** See [examples/minimal-terminal.py](examples/minimal-terminal.py) -- a 50-line terminal emulator in Python using the `pty` module:

```python
#!/usr/bin/env python3
"""Minimal terminal emulator in Python. Demonstrates PTY basics."""
import os
import pty
import sys
import select
import tty
import termios
import signal

def main():
    # Save original terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # forkpty: creates a PTY, forks, connects child to slave
        pid, master_fd = pty.fork()

        if pid == 0:
            # Child: execute shell
            os.environ['TERM'] = 'xterm-256color'
            shell = os.environ.get('SHELL', '/bin/sh')
            os.execlp(shell, shell)

        # Parent: set raw mode on our own stdin
        tty.setraw(sys.stdin)

        while True:
            rlist, _, _ = select.select([sys.stdin, master_fd], [], [], 0.1)

            if sys.stdin in rlist:
                data = os.read(sys.stdin.fileno(), 1024)
                if not data:
                    break
                os.write(master_fd, data)

            if master_fd in rlist:
                try:
                    data = os.read(master_fd, 4096)
                    if not data:
                        break
                    os.write(sys.stdout.fileno(), data)
                except OSError:
                    break

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

if __name__ == '__main__':
    main()
```

---

## Chapter 5: VT100/xterm Escape Code Parser

The escape code parser is the most complex and most critical component of your terminal emulator. It transforms a stream of bytes into a sequence of actions: print this character, move the cursor there, change the color to red, scroll up two lines, switch to the alternate screen. Getting the parser wrong means garbled output from every program you run.

![VT100 State Machine](assets/03-vt100-state-machine.svg)

### 5.1 Standards

The escape code system is governed by several overlapping standards:

**ECMA-48** (equivalent to ISO 6429): The primary standard for control functions in coded character sets. Published by ECMA International, freely available at `https://ecma-international.org/publications-and-standards/standards/ecma-48/`. ECMA-48 defines the structure of escape sequences (CSI, OSC, DCS, etc.), the state machine for parsing them, and a large set of standard control functions. This is the document you should read first.

**ANSI X3.64**: The original American national standard (1979) for control sequences, based on the DEC VT100 implementation. Functionally equivalent to ECMA-48 for the sequences that matter. When people say "ANSI escape codes," they mean this standard.

**DEC VT100-VT520 documentation**: DEC's terminal manuals define the specific behavior of each escape sequence, including edge cases and modes not covered by ECMA-48. The VT100 User Guide and VT220 Programmer Reference are essential references for understanding how sequences interact with terminal modes.

**xterm control sequences (ctlseqs)**: Thomas Dickey's comprehensive document covering every escape sequence that xterm supports, including extensions beyond the ANSI/ECMA-48 standards. This is the de facto reference for modern terminal emulators: `https://invisible-island.net/xterm/ctlseqs/ctlseqs.html`. When in doubt, implement what xterm does.

**The hierarchy of authority:** If ECMA-48 and xterm disagree, follow xterm. If xterm and DEC documentation disagree, follow xterm (because xterm is what programs target). If nothing documents a sequence, test in xterm and copy its behavior.

### 5.2 CSI Sequences

CSI (Control Sequence Introducer) sequences are the most common escape sequences. They control cursor movement, text attributes (colors), screen clearing, scrolling, and mode setting.

#### 5.2.1 Format

```
CSI = ESC [                        (7-bit: 0x1B 0x5B)
CSI = 0x9B                         (8-bit: single byte, rarely used)

Full format:
ESC [ <private-marker>? <params> <intermediate>? <final>

Where:
  private-marker: ? or > or = (optional, marks DEC private sequences)
  params:         semicolon-separated decimal numbers (e.g., "1;2;3")
  intermediate:   bytes 0x20-0x2F (space through /) (rarely used)
  final:          a single byte 0x40-0x7E (@ through ~) that identifies the command
```

Examples:
```
ESC[A        — CUU: Cursor Up 1 (default parameter = 1)
ESC[5A       — CUU: Cursor Up 5
ESC[2;10H    — CUP: Cursor Position row=2, col=10
ESC[31m      — SGR: Set foreground color to red
ESC[38;2;255;128;0m — SGR: Set foreground to true color RGB(255,128,0)
ESC[?1049h   — DECSET: Enable alternate screen buffer (private mode, note the ?)
```

#### 5.2.2 Important CSI Sequences Table

| Sequence | Name | Mnemonic | Description |
|---|---|---|---|
| `ESC[A` | CUU | Cursor Up | Move cursor up N rows (default 1) |
| `ESC[B` | CUD | Cursor Down | Move cursor down N rows |
| `ESC[C` | CUF | Cursor Forward | Move cursor right N columns |
| `ESC[D` | CUB | Cursor Back | Move cursor left N columns |
| `ESC[E` | CNL | Cursor Next Line | Move to beginning of line N lines down |
| `ESC[F` | CPL | Cursor Previous Line | Move to beginning of line N lines up |
| `ESC[G` | CHA | Cursor Horizontal Absolute | Move cursor to column N |
| `ESC[H` | CUP | Cursor Position | Move cursor to row N, column M (1-based) |
| `ESC[J` | ED | Erase in Display | 0=below, 1=above, 2=all, 3=all+scrollback |
| `ESC[K` | EL | Erase in Line | 0=right, 1=left, 2=entire line |
| `ESC[L` | IL | Insert Lines | Insert N blank lines at cursor |
| `ESC[M` | DL | Delete Lines | Delete N lines at cursor |
| `ESC[P` | DCH | Delete Characters | Delete N characters at cursor |
| `ESC[@` | ICH | Insert Characters | Insert N blank characters at cursor |
| `ESC[S` | SU | Scroll Up | Scroll up N lines |
| `ESC[T` | SD | Scroll Down | Scroll down N lines |
| `ESC[X` | ECH | Erase Characters | Erase N characters at cursor (no cursor movement) |
| `ESC[d` | VPA | Vertical Position Absolute | Move cursor to row N |
| `ESC[m` | SGR | Select Graphic Rendition | Set text attributes and colors |
| `ESC[n` | DSR | Device Status Report | Request cursor position (6=CPR) |
| `ESC[r` | DECSTBM | Set Top/Bottom Margins | Set scrolling region rows N to M |
| `ESC[s` | SCP | Save Cursor Position | Save cursor position (ANSI.SYS) |
| `ESC[u` | RCP | Restore Cursor Position | Restore cursor position (ANSI.SYS) |
| `ESC[t` | XTWINOPS | Window Operations | Resize, move, iconify window |
| `ESC[?h` | DECSET | DEC Private Mode Set | Enable various modes |
| `ESC[?l` | DECRST | DEC Private Mode Reset | Disable various modes |

**Important DEC Private Modes (ESC[?Nh / ESC[?Nl):**

| Mode N | Name | Effect |
|---|---|---|
| 1 | DECCKM | Application cursor keys (arrow keys send ESC O A instead of ESC [ A) |
| 6 | DECOM | Origin mode (cursor position relative to scroll region) |
| 7 | DECAWM | Auto-wrap mode (cursor wraps at right margin) |
| 12 | Cursor blink | Blinking cursor on/off |
| 25 | DECTCEM | Cursor visible (l=hidden, h=visible) |
| 47 | Alternate screen | Switch to/from alternate screen buffer (older) |
| 1000 | Mouse button tracking | Report mouse button press/release |
| 1002 | Mouse button+motion | Report button events and motion while pressed |
| 1003 | Mouse any-event | Report all mouse events including motion |
| 1006 | SGR mouse mode | Extended mouse coordinates (supports >223 columns) |
| 1049 | Alternate screen + cursor | Save cursor, switch to alt screen, clear it (modern) |
| 2004 | Bracketed paste | Wrap pasted text in ESC[200~ ... ESC[201~ |

### 5.3 OSC Sequences

OSC (Operating System Command) sequences carry higher-level commands, typically for window management and extended features.

#### 5.3.1 Format

```
OSC = ESC ]                   (0x1B 0x5D)

Full format:
ESC ] Ps ; Pt BEL             (terminated by BEL, 0x07)
ESC ] Ps ; Pt ST              (terminated by ST = ESC \, 0x1B 0x5C)

Where:
  Ps = numeric parameter (identifies the command)
  Pt = text parameter (the payload)
```

#### 5.3.2 Important OSC Sequences

| Sequence | Description |
|---|---|
| `ESC]0;text BEL` | Set window title and icon name |
| `ESC]1;text BEL` | Set icon name only |
| `ESC]2;text BEL` | Set window title only |
| `ESC]4;N;spec BEL` | Set color N in the 256-color palette (e.g., `ESC]4;1;rgb:ff/00/00 BEL` sets color 1 to red) |
| `ESC]7;url BEL` | Set working directory (used by shells for tab/window cloning) |
| `ESC]8;params;uri ST` | Hyperlink -- make subsequent text a clickable link (supported by iTerm2, VTE, WezTerm, Ghostty) |
| `ESC]9;text BEL` | Desktop notification (iTerm2, ConEmu) |
| `ESC]10;spec BEL` | Set/query default foreground color |
| `ESC]11;spec BEL` | Set/query default background color |
| `ESC]12;spec BEL` | Set/query cursor color |
| `ESC]52;c;base64 BEL` | Clipboard access -- read or write the system clipboard (c=clipboard, p=primary selection; data is base64-encoded) |
| `ESC]133;A BEL` | Shell integration: mark prompt start (used by iTerm2, WezTerm for command detection) |
| `ESC]1337;...BEL` | iTerm2 proprietary sequences (inline images, badges, etc.) |

**OSC 8 (Hyperlinks):** This is an increasingly important feature. Programs like `ls --hyperlink`, `gcc` (error messages with file links), and `grep --hyperlink` emit OSC 8 sequences so terminal emulators can make text clickable:

```
ESC]8;params;https://example.com ST
This text is a hyperlink
ESC]8;; ST
```

The `params` field can contain `id=value` to group multiple text segments into a single logical hyperlink (so they highlight together).

**OSC 52 (Clipboard):** Allows programs running in the terminal (even over SSH) to access the system clipboard. This is a security-sensitive feature--your terminal should prompt the user or limit clipboard access to avoid malicious scripts stealing clipboard contents.

### 5.4 SGR Colors

SGR (Select Graphic Rendition) is the CSI `m` command. It controls text attributes and colors. Multiple parameters can be combined in a single sequence, separated by semicolons.

#### 5.4.1 Text Attributes

| Code | Attribute | Reset Code |
|---|---|---|
| 0 | Reset all attributes | -- |
| 1 | Bold (increased intensity) | 22 |
| 2 | Dim (decreased intensity) | 22 |
| 3 | Italic | 23 |
| 4 | Underline | 24 |
| 5 | Slow blink (<150/min) | 25 |
| 6 | Rapid blink (>150/min) | 25 |
| 7 | Reverse video (swap fg/bg) | 27 |
| 8 | Hidden (invisible) | 28 |
| 9 | Strikethrough | 29 |
| 21 | Double underline | 24 |
| 53 | Overline | 55 |
| 4:0 | Underline off | -- |
| 4:1 | Single underline | -- |
| 4:2 | Double underline | -- |
| 4:3 | Curly underline (undercurl) | -- |
| 4:4 | Dotted underline | -- |
| 4:5 | Dashed underline | -- |
| 58;2;R;G;B | Underline color (true color) | 59 |
| 58;5;N | Underline color (256 palette) | 59 |

#### 5.4.2 16 Standard Colors (3/4-bit)

| Code | Foreground | Code | Background | Color |
|---|---|---|---|---|
| 30 | Standard | 40 | Standard | Black |
| 31 | Standard | 41 | Standard | Red |
| 32 | Standard | 42 | Standard | Green |
| 33 | Standard | 43 | Standard | Yellow |
| 34 | Standard | 44 | Standard | Blue |
| 35 | Standard | 45 | Standard | Magenta |
| 36 | Standard | 46 | Standard | Cyan |
| 37 | Standard | 47 | Standard | White |
| 39 | Default fg | 49 | Default bg | -- |
| 90 | Bright | 100 | Bright | Black (Gray) |
| 91 | Bright | 101 | Bright | Red |
| 92 | Bright | 102 | Bright | Green |
| 93 | Bright | 103 | Bright | Yellow |
| 94 | Bright | 104 | Bright | Blue |
| 95 | Bright | 105 | Bright | Magenta |
| 96 | Bright | 106 | Bright | Cyan |
| 97 | Bright | 107 | Bright | White |

These 16 colors are configurable in the terminal's color scheme. The actual RGB values differ between terminals and themes. "Red" (color 1/31) might be `#CC0000` in one theme and `#FF6B6B` in another.

#### 5.4.3 256-Color Palette (8-bit)

```
ESC[38;5;Nm    — Set foreground to color N (0-255)
ESC[48;5;Nm    — Set background to color N (0-255)
```

The 256 colors are divided into:

| Range | Description |
|---|---|
| 0-7 | Standard colors (same as 30-37) |
| 8-15 | Bright colors (same as 90-97) |
| 16-231 | 6x6x6 color cube: `16 + 36*r + 6*g + b` where r,g,b are 0-5 |
| 232-255 | 24-step grayscale: `8 + 10*(N-232)` gives gray levels from 8 to 238 |

To convert a 256-color index to RGB:

```rust
fn color256_to_rgb(n: u8) -> (u8, u8, u8) {
    match n {
        0..=15 => {
            // Standard and bright colors (lookup table)
            STANDARD_COLORS[n as usize]
        }
        16..=231 => {
            // 6x6x6 color cube
            let n = n - 16;
            let b = n % 6;
            let g = (n / 6) % 6;
            let r = n / 36;
            let to_byte = |c: u8| if c == 0 { 0 } else { 55 + 40 * c };
            (to_byte(r), to_byte(g), to_byte(b))
        }
        232..=255 => {
            // Grayscale ramp
            let v = 8 + 10 * (n - 232);
            (v, v, v)
        }
    }
}
```

#### 5.4.4 True Color (24-bit)

```
ESC[38;2;R;G;Bm    — Set foreground to RGB(R,G,B)
ESC[48;2;R;G;Bm    — Set background to RGB(R,G,B)
```

True color support was pioneered by xterm and is now supported by virtually all modern terminals. The `COLORTERM=truecolor` environment variable advertises support. There is no formal standard for this--it is a de facto convention.

**Colon vs semicolon:** Some terminals and standards use colons as subparameter separators: `ESC[38:2:R:G:Bm`. The colon form is technically more correct per ECMA-48 (colons separate subparameters within a parameter, while semicolons separate parameters). Your parser should support both forms.

#### 5.4.5 Example SGR Sequence

```
ESC[1;3;38;2;255;165;0m
```

This sets: bold (1) + italic (3) + foreground true color RGB(255, 165, 0) (orange). The parser splits on semicolons, processes each parameter or parameter group:
- `1` -> enable bold
- `3` -> enable italic
- `38;2;255;165;0` -> set foreground to RGB(255, 165, 0) (consumes 5 parameters)

### 5.5 State Machine Design (Paul Williams Model)

The parser for VT100/xterm escape sequences is best implemented as a deterministic finite automaton (DFA). Paul Williams published a clean state machine model at `https://vt100.net/emu/dec_ansi_parser` that has become the standard reference for terminal parser implementations.

#### 5.5.1 States

| State | Description |
|---|---|
| **Ground** | Default state. Printable characters are displayed. Control characters (0x00-0x1F) are executed immediately. |
| **Escape** | Entered on ESC (0x1B). Waiting for the next byte to determine the sequence type. |
| **EscapeIntermediate** | Escape sequence has intermediate bytes (0x20-0x2F). Collecting before the final byte. |
| **CsiEntry** | Entered on `[` after ESC. Beginning of a CSI sequence. |
| **CsiParam** | Collecting parameter bytes (0x30-0x39 digits, 0x3B semicolon, 0x3A colon). |
| **CsiIntermediate** | Collecting intermediate bytes (0x20-0x2F) between parameters and the final byte. |
| **CsiIgnore** | Invalid CSI sequence detected. Consuming bytes until the final byte, then discarding. |
| **OscString** | Collecting an OSC string (after ESC ]). Terminated by BEL (0x07) or ST (ESC \\). |
| **DcsEntry** | Entered on `P` after ESC. Beginning of a DCS (Device Control String) sequence. |
| **DcsParam** | Collecting DCS parameters. |
| **DcsIntermediate** | Collecting DCS intermediate bytes. |
| **DcsPassthrough** | DCS content pass-through. Bytes are forwarded to a DCS handler until ST. |
| **DcsIgnore** | Invalid DCS sequence. Consuming until ST. |
| **SosPmApcString** | Collecting SOS/PM/APC strings (rarely used). |

#### 5.5.2 Key Transitions

The state machine is driven by byte ranges:

```
Ground state:
  0x00-0x17, 0x19, 0x1C-0x1F  -> execute (C0 control character)
  0x1B                          -> transition to Escape
  0x20-0x7E                     -> print (displayable character)
  0x7F                          -> ignore (DEL in Ground)
  0x80-0x8F, 0x91-0x97, 0x99, 0x9A -> execute (C1 control, 8-bit)
  0x90                          -> transition to DcsEntry (DCS, 8-bit)
  0x9B                          -> transition to CsiEntry (CSI, 8-bit)
  0x9C                          -> (ST, 8-bit) - ignored in Ground
  0x9D                          -> transition to OscString (OSC, 8-bit)
  0x9E, 0x9F                    -> transition to SosPmApcString
  0xA0-0xFF                     -> print (Latin-1 supplement / UTF-8 start bytes)

Escape state:
  0x1B                          -> transition to Escape (re-entry)
  0x20-0x2F                     -> transition to EscapeIntermediate, collect
  0x30-0x4F, 0x51-0x57, 0x59-0x5A, 0x5C, 0x60-0x7E -> dispatch ESC sequence, -> Ground
  0x50                          -> transition to DcsEntry (ESC P)
  0x58, 0x5E, 0x5F              -> transition to SosPmApcString
  0x5B                          -> transition to CsiEntry (ESC [)
  0x5D                          -> transition to OscString (ESC ])
  0x7F                          -> ignore

CsiEntry state:
  0x20-0x2F                     -> transition to CsiIntermediate, collect
  0x30-0x39, 0x3B               -> transition to CsiParam, collect (param digit or ;)
  0x3A                          -> transition to CsiIgnore (colon in wrong position)
  0x3C-0x3F                     -> transition to CsiParam, collect (private marker: < = > ?)
  0x40-0x7E                     -> dispatch CSI, -> Ground (no params)
  0x7F                          -> ignore

CsiParam state:
  0x20-0x2F                     -> transition to CsiIntermediate, collect
  0x30-0x39, 0x3A, 0x3B         -> collect (digits, colon, semicolon)
  0x3C-0x3F                     -> transition to CsiIgnore (private marker in wrong position)
  0x40-0x7E                     -> dispatch CSI, -> Ground
  0x7F                          -> ignore
```

#### 5.5.3 Rust Implementation Sketch

```rust
/// Terminal parser states (Paul Williams model)
#[derive(Debug, Clone, Copy, PartialEq)]
enum State {
    Ground,
    Escape,
    EscapeIntermediate,
    CsiEntry,
    CsiParam,
    CsiIntermediate,
    CsiIgnore,
    OscString,
    DcsEntry,
    DcsParam,
    DcsIntermediate,
    DcsPassthrough,
    DcsIgnore,
    SosPmApcString,
}

/// Actions the parser can emit
#[derive(Debug)]
enum Action {
    Print(char),
    Execute(u8),            // C0 control character
    CsiDispatch {
        params: Vec<Vec<u16>>,  // Parameters (with subparameters via colon)
        intermediates: Vec<u8>,
        private_marker: Option<u8>,
        final_byte: u8,
    },
    OscDispatch {
        params: Vec<Vec<u8>>,   // OSC parameters separated by ;
    },
    EscDispatch {
        intermediates: Vec<u8>,
        final_byte: u8,
    },
    DcsHook { /* ... */ },
    DcsPut(u8),
    DcsUnhook,
}

struct Parser {
    state: State,
    params: Vec<Vec<u16>>,
    current_param: u16,
    intermediates: Vec<u8>,
    private_marker: Option<u8>,
    osc_buffer: Vec<u8>,
    // UTF-8 accumulation
    utf8_buffer: [u8; 4],
    utf8_len: usize,
    utf8_expected: usize,
}

impl Parser {
    fn new() -> Self {
        Parser {
            state: State::Ground,
            params: Vec::new(),
            current_param: 0,
            intermediates: Vec::new(),
            private_marker: None,
            osc_buffer: Vec::new(),
            utf8_buffer: [0; 4],
            utf8_len: 0,
            utf8_expected: 0,
        }
    }

    /// Process a single byte and return zero or more actions.
    fn advance(&mut self, byte: u8) -> Vec<Action> {
        let mut actions = Vec::new();

        // Handle anywhere transitions first (ESC can interrupt any state)
        if byte == 0x1B && self.state != State::Escape {
            // Cancel current sequence, enter Escape
            self.clear_params();
            self.state = State::Escape;
            return actions;
        }

        match self.state {
            State::Ground => {
                match byte {
                    0x00..=0x1A | 0x1C..=0x1F => {
                        actions.push(Action::Execute(byte));
                    }
                    0x1B => {
                        self.state = State::Escape;
                    }
                    0x20..=0x7E => {
                        actions.push(Action::Print(byte as char));
                    }
                    0x7F => {} // DEL, ignore in Ground
                    0x80..=0xFF => {
                        // UTF-8 handling
                        if let Some(ch) = self.accumulate_utf8(byte) {
                            actions.push(Action::Print(ch));
                        }
                    }
                }
            }

            State::Escape => {
                match byte {
                    0x20..=0x2F => {
                        self.intermediates.push(byte);
                        self.state = State::EscapeIntermediate;
                    }
                    0x5B => {
                        // ESC [ -> CSI
                        self.clear_params();
                        self.state = State::CsiEntry;
                    }
                    0x5D => {
                        // ESC ] -> OSC
                        self.osc_buffer.clear();
                        self.state = State::OscString;
                    }
                    0x50 => {
                        // ESC P -> DCS
                        self.clear_params();
                        self.state = State::DcsEntry;
                    }
                    0x30..=0x4F | 0x51..=0x57 | 0x59..=0x5A | 0x5C | 0x60..=0x7E => {
                        actions.push(Action::EscDispatch {
                            intermediates: self.intermediates.clone(),
                            final_byte: byte,
                        });
                        self.state = State::Ground;
                    }
                    _ => {
                        self.state = State::Ground;
                    }
                }
            }

            State::CsiEntry => {
                match byte {
                    0x30..=0x39 => {
                        self.current_param = (byte - b'0') as u16;
                        self.state = State::CsiParam;
                    }
                    0x3B => {
                        // Semicolon: empty parameter (use default)
                        self.params.push(vec![0]);
                        self.state = State::CsiParam;
                    }
                    0x3C..=0x3F => {
                        // Private marker: ? > = <
                        self.private_marker = Some(byte);
                        self.state = State::CsiParam;
                    }
                    0x40..=0x7E => {
                        // Final byte with no params
                        actions.push(Action::CsiDispatch {
                            params: self.params.clone(),
                            intermediates: self.intermediates.clone(),
                            private_marker: self.private_marker,
                            final_byte: byte,
                        });
                        self.state = State::Ground;
                    }
                    0x20..=0x2F => {
                        self.intermediates.push(byte);
                        self.state = State::CsiIntermediate;
                    }
                    _ => {
                        self.state = State::CsiIgnore;
                    }
                }
            }

            State::CsiParam => {
                match byte {
                    0x30..=0x39 => {
                        // Digit: accumulate parameter
                        self.current_param = self.current_param
                            .saturating_mul(10)
                            .saturating_add((byte - b'0') as u16);
                    }
                    0x3B => {
                        // Semicolon: end current parameter, start next
                        self.push_param();
                    }
                    0x3A => {
                        // Colon: subparameter separator
                        self.push_subparam();
                    }
                    0x40..=0x7E => {
                        // Final byte: dispatch
                        self.push_param();
                        actions.push(Action::CsiDispatch {
                            params: self.params.clone(),
                            intermediates: self.intermediates.clone(),
                            private_marker: self.private_marker,
                            final_byte: byte,
                        });
                        self.state = State::Ground;
                    }
                    0x20..=0x2F => {
                        self.push_param();
                        self.intermediates.push(byte);
                        self.state = State::CsiIntermediate;
                    }
                    _ => {
                        self.state = State::CsiIgnore;
                    }
                }
            }

            State::OscString => {
                match byte {
                    0x07 => {
                        // BEL: terminate OSC string
                        let osc_data = self.osc_buffer.clone();
                        let params: Vec<Vec<u8>> = osc_data
                            .split(|&b| b == b';')
                            .map(|s| s.to_vec())
                            .collect();
                        actions.push(Action::OscDispatch { params });
                        self.state = State::Ground;
                    }
                    0x1B => {
                        // Might be ST (ESC \)
                        // We handle this via the "anywhere" ESC transition above,
                        // then check for backslash in Escape state.
                        // Simplified: treat ESC in OSC as terminator.
                        let osc_data = self.osc_buffer.clone();
                        let params: Vec<Vec<u8>> = osc_data
                            .split(|&b| b == b';')
                            .map(|s| s.to_vec())
                            .collect();
                        actions.push(Action::OscDispatch { params });
                        self.state = State::Escape; // To handle the \ if it follows
                    }
                    _ => {
                        self.osc_buffer.push(byte);
                    }
                }
            }

            // ... additional states (DCS, CsiIntermediate, CsiIgnore, etc.)
            _ => {}
        }

        actions
    }

    fn clear_params(&mut self) {
        self.params.clear();
        self.current_param = 0;
        self.intermediates.clear();
        self.private_marker = None;
    }

    fn push_param(&mut self) {
        self.params.push(vec![self.current_param]);
        self.current_param = 0;
    }

    fn push_subparam(&mut self) {
        if let Some(last) = self.params.last_mut() {
            last.push(self.current_param);
        } else {
            self.params.push(vec![self.current_param]);
        }
        self.current_param = 0;
    }

    fn accumulate_utf8(&mut self, byte: u8) -> Option<char> {
        if self.utf8_len == 0 {
            // Start of a new UTF-8 sequence
            if byte & 0xE0 == 0xC0 {
                self.utf8_expected = 2;
            } else if byte & 0xF0 == 0xE0 {
                self.utf8_expected = 3;
            } else if byte & 0xF8 == 0xF0 {
                self.utf8_expected = 4;
            } else {
                // Invalid start byte, emit replacement character
                return Some('\u{FFFD}');
            }
            self.utf8_buffer[0] = byte;
            self.utf8_len = 1;

            if self.utf8_len == self.utf8_expected {
                return self.flush_utf8();
            }
            None
        } else {
            // Continuation byte
            if byte & 0xC0 != 0x80 {
                // Invalid continuation, reset and emit replacement
                self.utf8_len = 0;
                return Some('\u{FFFD}');
            }
            self.utf8_buffer[self.utf8_len] = byte;
            self.utf8_len += 1;

            if self.utf8_len == self.utf8_expected {
                return self.flush_utf8();
            }
            None
        }
    }

    fn flush_utf8(&mut self) -> Option<char> {
        let s = std::str::from_utf8(&self.utf8_buffer[..self.utf8_len]).ok()?;
        self.utf8_len = 0;
        s.chars().next()
    }
}
```

### 5.6 Implementation: vte Crate vs Hand-Rolling

For a Rust terminal emulator, you have two choices for the escape sequence parser:

**Option 1: Use the `vte` crate.** This is the parser used by Alacritty. It implements the Paul Williams state machine with excellent performance (zero allocations, table-driven transitions). You provide a `Perform` trait implementation that receives callbacks for print, execute, CSI dispatch, OSC dispatch, etc.

```rust
use vte::{Parser, Perform};

struct MyTerminal {
    // terminal state: grid, cursor, colors, etc.
}

impl Perform for MyTerminal {
    fn print(&mut self, c: char) {
        // Insert character at cursor position
        self.grid[self.cursor.row][self.cursor.col] = Cell::new(c, self.current_attrs);
        self.advance_cursor();
    }

    fn execute(&mut self, byte: u8) {
        match byte {
            0x07 => self.bell(),          // BEL
            0x08 => self.backspace(),     // BS
            0x09 => self.tab(),           // HT
            0x0A => self.line_feed(),     // LF
            0x0D => self.carriage_return(), // CR
            _ => {}
        }
    }

    fn csi_dispatch(&mut self, params: &vte::Params, intermediates: &[u8],
                    ignore: bool, action: char) {
        if ignore { return; }
        match action {
            'A' => self.cursor_up(params.get(0).unwrap_or(1)),
            'B' => self.cursor_down(params.get(0).unwrap_or(1)),
            'C' => self.cursor_forward(params.get(0).unwrap_or(1)),
            'D' => self.cursor_back(params.get(0).unwrap_or(1)),
            'H' => {
                let row = params.get(0).unwrap_or(1);
                let col = params.get(1).unwrap_or(1);
                self.cursor_position(row, col);
            }
            'J' => self.erase_display(params.get(0).unwrap_or(0)),
            'K' => self.erase_line(params.get(0).unwrap_or(0)),
            'm' => self.set_graphic_rendition(params),
            // ... hundreds more
            _ => {}
        }
    }

    fn osc_dispatch(&mut self, params: &[&[u8]], bell_terminated: bool) {
        if params.is_empty() { return; }
        match params[0] {
            b"0" | b"2" => {
                // Set window title
                if let Some(title) = params.get(1) {
                    self.set_title(String::from_utf8_lossy(title).into());
                }
            }
            b"52" => {
                // Clipboard access
                self.handle_clipboard(params);
            }
            _ => {}
        }
    }

    // ... esc_dispatch, hook, put, unhook
}

// Usage:
let mut parser = Parser::new();
let mut terminal = MyTerminal::new();

// Feed bytes from the PTY
let bytes_from_pty: &[u8] = &[0x1B, b'[', b'3', b'1', b'm', b'H', b'e', b'l', b'l', b'o'];
for byte in bytes_from_pty {
    parser.advance(&mut terminal, *byte);
}
```

**Option 2: Hand-roll the parser.** This gives you complete control over edge cases, performance characteristics, and error handling. Ghostty takes this approach (Zig implementation). The main advantage is that you can optimize for your specific needs--for example, SIMD-accelerating the "printable characters in Ground state" fast path, which is the most common case (>95% of bytes in typical terminal output are printable ASCII).

**Recommendation:** Use the `vte` crate for your first implementation. It is battle-tested, correct, and fast. Once your terminal is working, you can replace it with a custom parser if profiling shows the parser as a bottleneck (unlikely--rendering is almost always the bottleneck).

---

## Chapter 6: Rendering -- Drawing Characters on Screen

Rendering is where theory meets pixels. Your parser has updated the grid; now you need to draw it. The choice of rendering technology has the largest impact on your terminal's performance, visual quality, and platform compatibility.

![GPU Rendering Pipeline](assets/04-gpu-rendering-pipeline.svg)

### 6.1 CPU Rendering

CPU rendering uses the operating system's 2D graphics APIs to draw text. This was the universal approach before 2016.

**NSTextView / CoreText (macOS, iTerm2).** iTerm2 uses CoreText for text rendering on macOS. CoreText handles font fallback, ligatures, bidirectional text, and emoji natively. The rendering path: for each row of the terminal grid, build an attributed string with the correct fonts and colors, then draw it using CoreText's line-based layout engine. This is correct and featureful but slow for large grids--CoreText was designed for document layout, not for rendering 10,000 character cells 60 times per second.

**VTE / GTK / Cairo (Linux, GNOME Terminal).** The VTE widget renders using Cairo (a 2D graphics library) with Pango for text shaping. Cairo draws to an X11 or Wayland surface. Like CoreText, this is correct for text but not optimized for grid rendering.

**GDI / DirectWrite (Windows, cmd.exe).** The legacy Windows console used GDI (Graphics Device Interface) for text rendering. GDI is ancient and slow. Modern Windows Terminal uses DirectWrite for text shaping and a custom GPU renderer for display.

**Performance ceiling of CPU rendering:** A typical CPU renderer can achieve 5-15ms frame times for an 80x24 terminal. For larger terminals (200x50 = 10,000 cells) or rapid scrolling (catting a large file), CPU renderers often hit 30-50ms per frame, causing visible stuttering. The fundamental problem is that CPU text rendering is sequential: each glyph is rasterized and composited individually. GPUs parallelize this trivially.

### 6.2 GPU Rendering Fundamentals

A GPU processes thousands of operations in parallel. Terminal rendering maps naturally to GPU architecture:

1. **Each character cell is an independent quad** (two triangles forming a rectangle). The cells do not depend on each other, so they can all be processed in parallel.

2. **Glyph rendering is texture sampling.** Pre-rasterize all needed glyphs into a single texture (the glyph atlas). Drawing a character means sampling from the correct region of this texture. Texture sampling is the GPU's core competency.

3. **Colors and attributes are per-vertex data.** Foreground color, background color, and attribute flags are passed as vertex attributes or uniform data. The fragment shader combines the glyph texture with the colors.

The GPU rendering pipeline for a terminal:

```
1. Build glyph atlas (one-time, updated as new glyphs are needed)
2. For each visible cell in the grid:
   a. Look up the glyph's position in the atlas
   b. Emit a quad (4 vertices) with:
      - Screen position (cell row, column -> pixel coordinates)
      - Texture coordinates (glyph location in atlas)
      - Foreground and background colors
      - Attribute flags (bold, italic, etc.)
3. Upload vertex data to GPU
4. Execute render pass:
   a. Vertex shader: transform cell coordinates to screen coordinates
   b. Fragment shader: sample glyph texture, apply fg/bg colors
5. Present frame
```

This processes all 10,000+ cells in a single draw call, completing in 1-3ms on modern GPUs.

### 6.3 Font Atlas / Glyph Cache

The glyph atlas is a single large texture (e.g., 1024x1024 or 2048x2048 pixels) containing pre-rasterized images of every glyph the terminal has encountered. When a new character appears that is not in the atlas, it is rasterized and packed into an empty region of the texture.

#### 6.3.1 Rasterization

**FreeType** is the standard library for rasterizing font outlines (TrueType, OpenType) into bitmaps. Given a font file and a character code, FreeType produces a grayscale bitmap of the glyph at the requested size.

```c
#include <ft2build.h>
#include FT_FREETYPE_H

FT_Library library;
FT_Face face;

FT_Init_FreeType(&library);
FT_New_Face(library, "/path/to/font.ttf", 0, &face);
FT_Set_Pixel_Sizes(face, 0, 16);  // 16px height

// Rasterize the glyph for 'A'
FT_Load_Char(face, 'A', FT_LOAD_RENDER);

// face->glyph->bitmap now contains the rasterized glyph:
//   .width, .rows: dimensions
//   .buffer: grayscale pixel data (1 byte per pixel)
//   .pitch: bytes per row
// face->glyph->bitmap_left, bitmap_top: positioning offsets
// face->glyph->advance.x: horizontal advance (in 1/64 pixels)
```

**CoreText (macOS)** can be used instead of FreeType on macOS. CoreText handles Apple-specific font features (SF Pro, variable fonts) better than FreeType.

**Subpixel rendering:** LCD subpixel rendering (ClearType on Windows, LCD smoothing on macOS) renders glyphs with color components (RGB) instead of grayscale, using the LCD's subpixel layout for higher effective resolution. This requires a 3-channel (RGB) glyph atlas instead of single-channel (grayscale). Alacritty supports subpixel rendering; Ghostty defaults to grayscale anti-aliasing for simplicity and consistency.

#### 6.3.2 Shaping

Text shaping transforms a sequence of Unicode code points into a sequence of positioned glyphs. This is necessary for:
- **Ligatures:** Programming fonts like Fira Code transform `->` into a single arrow glyph, `!=` into a single not-equal glyph, etc.
- **Combining characters:** `e` + combining acute accent (U+0301) = `e` (single glyph).
- **Arabic/Hebrew/Devanagari:** Characters change shape based on their position in a word.
- **Kerning:** Adjusting spacing between specific character pairs.

**HarfBuzz** is the standard shaping library. Given a font and a string, it produces a sequence of glyph IDs with x/y offsets:

```c
hb_buffer_t *buf = hb_buffer_create();
hb_buffer_add_utf8(buf, "->", -1, 0, -1);
hb_buffer_set_direction(buf, HB_DIRECTION_LTR);
hb_buffer_set_script(buf, HB_SCRIPT_COMMON);

hb_font_t *font = hb_ft_font_create(ft_face, NULL);
hb_shape(font, buf, NULL, 0);

unsigned int glyph_count;
hb_glyph_info_t *glyph_info = hb_buffer_get_glyph_infos(buf, &glyph_count);
hb_glyph_position_t *glyph_pos = hb_buffer_get_glyph_positions(buf, &glyph_count);
// If the font has a ligature for "->", glyph_count will be 1 instead of 2
```

For terminal emulators, shaping is applied **per cell cluster**, not per line. Each grapheme cluster (which may be one or more Unicode code points) is shaped independently (or in small runs for ligature detection). This is different from a text editor, which shapes entire paragraphs.

#### 6.3.3 Atlas Packing

When a new glyph is rasterized, it must be placed in the atlas texture. Common packing algorithms:

**Shelf packing (row-based):** The simplest algorithm. The atlas is divided into horizontal "shelves." Each new glyph is placed on the current shelf if it fits; otherwise, a new shelf is started. The shelf height is the maximum glyph height in that row.

```rust
struct ShelfPacker {
    width: u32,           // Atlas width in pixels
    height: u32,          // Atlas height in pixels
    shelf_y: u32,         // Y position of current shelf
    shelf_height: u32,    // Height of current shelf
    cursor_x: u32,        // X position in current shelf
}

impl ShelfPacker {
    fn allocate(&mut self, glyph_w: u32, glyph_h: u32) -> Option<(u32, u32)> {
        // Does it fit on the current shelf?
        if self.cursor_x + glyph_w <= self.width
           && self.shelf_y + glyph_h <= self.height {
            let pos = (self.cursor_x, self.shelf_y);
            self.cursor_x += glyph_w;
            self.shelf_height = self.shelf_height.max(glyph_h);
            return Some(pos);
        }

        // Start a new shelf
        self.shelf_y += self.shelf_height;
        self.cursor_x = 0;
        self.shelf_height = glyph_h;

        if self.cursor_x + glyph_w <= self.width
           && self.shelf_y + glyph_h <= self.height {
            let pos = (self.cursor_x, self.shelf_y);
            self.cursor_x += glyph_w;
            return Some(pos);
        }

        None // Atlas is full
    }
}
```

**Skyline packing:** More space-efficient than shelf packing. Tracks the highest point at each X coordinate and places glyphs in the lowest available gap. Used by Alacritty.

**When the atlas fills up:** Either resize the atlas (re-upload to GPU) or evict least-recently-used glyphs (complex). For terminals, the atlas rarely fills up because the character set is limited. A 1024x1024 grayscale atlas can hold approximately 3,000-5,000 glyphs at 14px font size.

### 6.4 OpenGL Pipeline (Alacritty)

Alacritty uses OpenGL 3.3 Core Profile, which is supported on Linux (Mesa), macOS (deprecated but functional through 4.1), and Windows (any GPU from the last decade).

The rendering approach:

1. **Vertex buffer:** Each cell generates a quad (4 vertices, or 6 if using separate triangles). Each vertex has:
   - Position (x, y in pixels or normalized device coordinates)
   - Texture coordinates (u, v into the glyph atlas)
   - Foreground color (r, g, b, a)
   - Background color (r, g, b, a)

2. **Two-pass rendering:**
   - Pass 1: Draw backgrounds. A single full-screen quad per row (or per run of same-background cells) with the background color. This is done with a simple flat-color shader.
   - Pass 2: Draw foreground glyphs. For each cell with a printable character, sample the glyph atlas and apply the foreground color.

3. **Vertex shader (simplified):**

```glsl
#version 330 core

layout(location = 0) in vec2 position;   // Cell position in pixels
layout(location = 1) in vec2 uv;         // Texture coordinate in atlas
layout(location = 2) in vec4 fg_color;   // Foreground RGBA
layout(location = 3) in vec4 bg_color;   // Background RGBA (used in pass 1)

uniform mat4 projection;  // Orthographic projection matrix

out vec2 tex_coord;
out vec4 frag_fg;
out vec4 frag_bg;

void main() {
    gl_Position = projection * vec4(position, 0.0, 1.0);
    tex_coord = uv;
    frag_fg = fg_color;
    frag_bg = bg_color;
}
```

4. **Fragment shader for glyph rendering (simplified):**

```glsl
#version 330 core

in vec2 tex_coord;
in vec4 frag_fg;

uniform sampler2D glyph_atlas;

out vec4 out_color;

void main() {
    // Sample glyph alpha from the atlas (grayscale = alpha channel)
    float alpha = texture(glyph_atlas, tex_coord).r;

    // Apply foreground color with glyph alpha
    out_color = vec4(frag_fg.rgb, frag_fg.a * alpha);
}
```

For subpixel rendering, the fragment shader becomes more complex: it samples three alpha values (one per RGB subpixel channel) and applies them independently.

### 6.5 Metal Pipeline (Ghostty, iTerm2)

Metal is Apple's GPU API, available on macOS 10.11+ and iOS 8+. It offers lower overhead than OpenGL and is the recommended GPU API on Apple platforms (Apple deprecated OpenGL in macOS 10.14).

Key Metal concepts for terminal rendering:

```swift
import Metal
import MetalKit

class TerminalRenderer: NSObject, MTKViewDelegate {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let pipelineState: MTLRenderPipelineState
    let glyphAtlasTexture: MTLTexture
    var vertexBuffer: MTLBuffer?

    init(metalView: MTKView) {
        device = MTLCreateSystemDefaultDevice()!
        commandQueue = device.makeCommandQueue()!
        metalView.device = device
        metalView.colorPixelFormat = .bgra8Unorm

        // Load shaders
        let library = device.makeDefaultLibrary()!
        let vertexFunction = library.makeFunction(name: "vertex_main")!
        let fragmentFunction = library.makeFunction(name: "fragment_main")!

        // Create pipeline
        let descriptor = MTLRenderPipelineDescriptor()
        descriptor.vertexFunction = vertexFunction
        descriptor.fragmentFunction = fragmentFunction
        descriptor.colorAttachments[0].pixelFormat = .bgra8Unorm
        descriptor.colorAttachments[0].isBlendingEnabled = true
        descriptor.colorAttachments[0].sourceRGBBlendFactor = .sourceAlpha
        descriptor.colorAttachments[0].destinationRGBBlendFactor = .oneMinusSourceAlpha

        pipelineState = try! device.makeRenderPipelineState(descriptor: descriptor)

        // Create glyph atlas texture (1024x1024, single channel)
        let texDesc = MTLTextureDescriptor.texture2DDescriptor(
            pixelFormat: .r8Unorm,
            width: 1024, height: 1024,
            mipmapped: false
        )
        glyphAtlasTexture = device.makeTexture(descriptor: texDesc)!
    }

    func draw(in view: MTKView) {
        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let renderPassDescriptor = view.currentRenderPassDescriptor,
              let renderEncoder = commandBuffer.makeRenderCommandEncoder(
                  descriptor: renderPassDescriptor) else { return }

        renderEncoder.setRenderPipelineState(pipelineState)
        renderEncoder.setVertexBuffer(vertexBuffer, offset: 0, index: 0)
        renderEncoder.setFragmentTexture(glyphAtlasTexture, index: 0)

        // Draw all cells in one call
        let vertexCount = visibleCells * 6  // 6 vertices per quad (2 triangles)
        renderEncoder.drawPrimitives(type: .triangle, vertexStart: 0,
                                     vertexCount: vertexCount)

        renderEncoder.endEncoding()
        commandBuffer.present(view.currentDrawable!)
        commandBuffer.commit()
    }
}
```

Metal shader for glyph rendering:

```metal
#include <metal_stdlib>
using namespace metal;

struct VertexIn {
    float2 position [[attribute(0)]];
    float2 texCoord [[attribute(1)]];
    float4 fgColor  [[attribute(2)]];
    float4 bgColor  [[attribute(3)]];
};

struct VertexOut {
    float4 position [[position]];
    float2 texCoord;
    float4 fgColor;
    float4 bgColor;
};

vertex VertexOut vertex_main(VertexIn in [[stage_in]],
                              constant float4x4 &projection [[buffer(1)]]) {
    VertexOut out;
    out.position = projection * float4(in.position, 0.0, 1.0);
    out.texCoord = in.texCoord;
    out.fgColor = in.fgColor;
    out.bgColor = in.bgColor;
    return out;
}

fragment float4 fragment_main(VertexOut in [[stage_in]],
                               texture2d<float> glyphAtlas [[texture(0)]],
                               sampler texSampler [[sampler(0)]]) {
    float alpha = glyphAtlas.sample(texSampler, in.texCoord).r;
    // Blend foreground (glyph) over background
    float3 color = mix(in.bgColor.rgb, in.fgColor.rgb, alpha);
    return float4(color, 1.0);
}
```

Ghostty's Metal renderer is significantly more sophisticated: it uses instanced rendering (one instance per cell, reducing vertex data), texture arrays for multi-page atlases, and compute shaders for some operations.

### 6.6 Vulkan / DirectX 12 (Windows Terminal)

Vulkan and DirectX 12 are low-level, explicit GPU APIs. They give you maximum control over GPU resource management (memory allocation, synchronization, pipeline state) at the cost of significantly more code. A Vulkan triangle requires ~500 lines of boilerplate; an OpenGL triangle requires ~50.

**Windows Terminal** uses a DirectX 11 backend (simpler than DX12) with a custom atlas-based renderer. Its architecture:

1. **DirectWrite** for text shaping and glyph rasterization (replaces FreeType + HarfBuzz on Windows).
2. **Atlas texture** in GPU memory, updated via `ID3D11DeviceContext::UpdateSubresource()`.
3. **Instanced rendering:** Each cell is an instance with position, atlas coordinates, and colors.
4. **Custom shader** that handles cursor rendering, selection, and cell backgrounds in a single pass.

For a cross-platform terminal, Vulkan is not recommended as the primary renderer unless you are targeting Linux exclusively or need specific Vulkan features. The complexity overhead is substantial and the visual result is identical to OpenGL or Metal.

### 6.7 WebGPU / wgpu (Rio)

**wgpu** is a Rust implementation of the WebGPU standard. It provides a single, modern GPU API that maps to:
- Metal on macOS/iOS
- Vulkan on Linux/Android
- DirectX 12 on Windows
- OpenGL as a fallback

This is the most attractive option for a new cross-platform terminal in 2026, because you write rendering code once and it works on all platforms with native GPU backend performance.

```rust
use wgpu;

// Terminal renderer using wgpu
struct WgpuRenderer {
    device: wgpu::Device,
    queue: wgpu::Queue,
    surface: wgpu::Surface,
    pipeline: wgpu::RenderPipeline,
    glyph_atlas: wgpu::Texture,
    vertex_buffer: wgpu::Buffer,
    bind_group: wgpu::BindGroup,
}

impl WgpuRenderer {
    async fn new(window: &winit::window::Window) -> Self {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::all(),  // Metal, Vulkan, DX12, GL
            ..Default::default()
        });

        let surface = instance.create_surface(window).unwrap();

        let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: Some(&surface),
            force_fallback_adapter: false,
        }).await.unwrap();

        let (device, queue) = adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("Terminal GPU"),
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default(),
                memory_hints: wgpu::MemoryHints::Performance,
            },
            None,
        ).await.unwrap();

        // Create glyph atlas texture
        let glyph_atlas = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("Glyph Atlas"),
            size: wgpu::Extent3d { width: 1024, height: 1024, depth_or_array_layers: 1 },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::R8Unorm,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
            view_formats: &[],
        });

        // Shader module (WGSL - WebGPU Shading Language)
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Terminal Shader"),
            source: wgpu::ShaderSource::Wgsl(TERMINAL_SHADER.into()),
        });

        // ... pipeline setup, bind groups, vertex buffer layout
        // (follows standard wgpu patterns)

        todo!("Complete setup")
    }
}

const TERMINAL_SHADER: &str = r#"
struct VertexInput {
    @location(0) position: vec2<f32>,
    @location(1) tex_coord: vec2<f32>,
    @location(2) fg_color: vec4<f32>,
    @location(3) bg_color: vec4<f32>,
};

struct VertexOutput {
    @builtin(position) clip_position: vec4<f32>,
    @location(0) tex_coord: vec2<f32>,
    @location(1) fg_color: vec4<f32>,
    @location(2) bg_color: vec4<f32>,
};

@group(0) @binding(0) var<uniform> projection: mat4x4<f32>;
@group(0) @binding(1) var glyph_atlas: texture_2d<f32>;
@group(0) @binding(2) var atlas_sampler: sampler;

@vertex
fn vs_main(in: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    out.clip_position = projection * vec4<f32>(in.position, 0.0, 1.0);
    out.tex_coord = in.tex_coord;
    out.fg_color = in.fg_color;
    out.bg_color = in.bg_color;
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    let alpha = textureSample(glyph_atlas, atlas_sampler, in.tex_coord).r;
    let color = mix(in.bg_color.rgb, in.fg_color.rgb, alpha);
    return vec4<f32>(color, 1.0);
}
"#;
```

**Rio** (`https://github.com/nicedoc/rio`) demonstrates this approach in production. It achieves competitive performance with Alacritty while supporting all three major platforms through a single wgpu codebase.

### 6.8 Damage Tracking

Naive rendering redraws the entire grid every frame. At 60 FPS, this means processing and uploading 10,000+ cells per frame even if nothing changed. **Damage tracking** identifies which cells changed since the last frame and only re-renders those.

**Cell-level damage tracking (Alacritty):**

```rust
struct DamageTracker {
    /// Dirty flag per cell. Set when the cell is modified, cleared after rendering.
    dirty: Vec<Vec<bool>>,    // [row][col]
    /// Coarse damage: set when any cell in a row changed.
    dirty_rows: Vec<bool>,    // [row]
    /// Full damage: entire screen needs redraw (resize, scroll, etc.)
    full_damage: bool,
}

impl DamageTracker {
    fn mark_cell(&mut self, row: usize, col: usize) {
        self.dirty[row][col] = true;
        self.dirty_rows[row] = true;
    }

    fn mark_scroll(&mut self) {
        // Scrolling affects every row; mark full damage
        self.full_damage = true;
    }

    fn mark_resize(&mut self) {
        self.full_damage = true;
    }

    fn take_damage(&mut self) -> DamageReport {
        if self.full_damage {
            self.full_damage = false;
            self.clear_all();
            return DamageReport::Full;
        }

        let damaged_rows: Vec<usize> = self.dirty_rows.iter()
            .enumerate()
            .filter(|(_, &dirty)| dirty)
            .map(|(i, _)| i)
            .collect();

        self.clear_all();
        DamageReport::Partial(damaged_rows)
    }

    fn clear_all(&mut self) {
        for row in &mut self.dirty { row.fill(false); }
        self.dirty_rows.fill(false);
    }
}
```

**Ghostty's approach:** Ghostty tracks "dirty regions" (rectangular areas that changed) and only rebuilds the vertex data for those regions. The GPU draw call still covers the full screen (to avoid complex partial-rendering logic), but the vertex buffer upload is minimized.

**When damage tracking matters most:**
- Idle terminal (blinking cursor): Only 1-2 cells change per blink. Without damage tracking, you still redraw 10,000 cells 60 times per second. With damage tracking, you update 2 cells.
- Scrolling: Nearly every cell changes, so damage tracking gives no benefit. But scrolling is already fast because it is the GPU's strength.
- Typing: A few cells change per keystroke. Damage tracking reduces work significantly.

Power consumption is the primary benefit. A laptop with an idle terminal should not drain battery on unnecessary GPU work.

---

## Chapter 7: Grid Buffer and Unicode

The grid buffer is the terminal's model--the data structure that represents every character cell on screen and in the scrollback history. The renderer reads this data structure to draw the display. The parser writes to it when processing escape sequences.

![Character Cell Structure](assets/07-character-cell-structure.svg)

### 7.1 Character Cell Structure

Each cell in the terminal grid stores:

```rust
/// A single character cell in the terminal grid.
#[derive(Clone, Debug)]
struct Cell {
    /// The Unicode character (or first code point of a grapheme cluster).
    /// U+0000 means empty cell. U+FFFF can be used as a "wide char continuation"
    /// marker for the second cell of a CJK character.
    character: char,

    /// Extra code points for multi-codepoint grapheme clusters.
    /// Most cells need 0 extra code points. Combining marks and emoji ZWJ sequences
    /// can add 1-10 extra code points.
    /// Using SmallVec or inline array to avoid heap allocation for the common case.
    extra_codepoints: SmallVec<[char; 2]>,

    /// Foreground color
    fg: Color,

    /// Background color
    bg: Color,

    /// Cell attribute flags
    flags: CellFlags,

    /// Hyperlink ID (0 = no hyperlink). References into a hyperlink table.
    hyperlink_id: u16,
}

/// Color representation (supports all terminal color modes)
#[derive(Clone, Copy, Debug, PartialEq)]
enum Color {
    /// Default terminal foreground/background (theme-dependent)
    Default,
    /// Standard 16 colors (indices 0-15)
    Indexed(u8),
    /// 24-bit true color
    Rgb(u8, u8, u8),
}

bitflags::bitflags! {
    /// Cell attribute flags, packed into a single u16 for memory efficiency.
    #[derive(Clone, Copy, Debug)]
    struct CellFlags: u16 {
        const BOLD          = 0b0000_0000_0001;
        const DIM           = 0b0000_0000_0010;
        const ITALIC        = 0b0000_0000_0100;
        const UNDERLINE     = 0b0000_0000_1000;
        const BLINK         = 0b0000_0001_0000;
        const REVERSE       = 0b0000_0010_0000;
        const HIDDEN        = 0b0000_0100_0000;
        const STRIKETHROUGH = 0b0000_1000_0000;
        const WIDE          = 0b0001_0000_0000;  // This cell is a wide (CJK) character
        const WIDE_CONT     = 0b0010_0000_0000;  // Continuation of a wide character
        const WRAP          = 0b0100_0000_0000;  // Line was wrapped at this cell
        const DOUBLE_UNDERLINE = 0b1000_0000_0000;
    }
}
```

**Memory per cell:** With the structure above:
- `character`: 4 bytes (`char` in Rust is 4 bytes, Unicode scalar value)
- `extra_codepoints`: 0-8 bytes (SmallVec inline) or 24+ bytes (heap-allocated for complex emoji)
- `fg`: 4 bytes (enum with variants)
- `bg`: 4 bytes
- `flags`: 2 bytes
- `hyperlink_id`: 2 bytes
- **Total: ~16-24 bytes per cell** (common case, no extra code points and no padding issues)

Some implementations pack the cell more tightly:
- Alacritty uses ~20 bytes per cell.
- Ghostty uses a packed representation closer to 16 bytes.
- WezTerm uses a richer cell (supporting underline color, underline style) at ~32 bytes.

**The tradeoff:** Smaller cells mean less memory for scrollback and faster cache-line utilization during rendering. Richer cells mean fewer separate lookup tables but more memory per cell.

### 7.2 Scrollback Buffer

When text scrolls off the top of the visible screen, it is saved in the scrollback buffer so the user can scroll up to read it. The scrollback buffer is the terminal's "memory" of past output.

#### 7.2.1 Ring Buffer (Most Common)

A ring buffer has a fixed maximum size. When full, new lines overwrite the oldest lines. This is the standard implementation (Alacritty, Ghostty, VTE):

```rust
struct ScrollbackRingBuffer {
    /// Storage for all rows. Capacity = max_scrollback + visible_rows.
    rows: Vec<Row>,

    /// Index of the oldest valid row (the "top" of scrollback).
    head: usize,

    /// Total number of valid rows (capped at rows.len()).
    len: usize,

    /// Maximum scrollback lines.
    max_scrollback: usize,
}

struct Row {
    cells: Vec<Cell>,
    /// True if this row was wrapped from the previous row (no explicit newline).
    wrapped: bool,
}

impl ScrollbackRingBuffer {
    fn new(cols: usize, visible_rows: usize, max_scrollback: usize) -> Self {
        let capacity = visible_rows + max_scrollback;
        let mut rows = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            rows.push(Row {
                cells: vec![Cell::default(); cols],
                wrapped: false,
            });
        }

        ScrollbackRingBuffer {
            rows,
            head: 0,
            len: visible_rows,  // Start with only visible rows valid
            max_scrollback,
        }
    }

    /// Push a new line at the bottom. If at capacity, the oldest line is lost.
    fn push_line(&mut self) -> &mut Row {
        if self.len < self.rows.len() {
            self.len += 1;
        } else {
            // Ring buffer full: advance head (oldest line is overwritten)
            self.head = (self.head + 1) % self.rows.len();
        }
        let idx = (self.head + self.len - 1) % self.rows.len();
        self.rows[idx].clear();
        &mut self.rows[idx]
    }

    /// Get a row by index. 0 = oldest (top of scrollback), len-1 = newest.
    fn get(&self, index: usize) -> &Row {
        assert!(index < self.len);
        let physical = (self.head + index) % self.rows.len();
        &self.rows[physical]
    }
}
```

**Memory calculation for scrollback:**

| Grid Size | Scrollback Lines | Cells | Cell Size | Total Memory |
|---|---|---|---|---|
| 80x24 | 10,000 | 10,000 * 80 = 800,000 | 20 bytes | ~15 MB |
| 200x50 | 10,000 | 10,000 * 200 = 2,000,000 | 20 bytes | ~38 MB |
| 200x50 | 100,000 | 100,000 * 200 = 20,000,000 | 20 bytes | ~381 MB |

Alacritty defaults to 10,000 scrollback lines. iTerm2 allows configuring unlimited scrollback (which can consume gigabytes for long-running sessions). Ghostty defaults to 10,000.

For memory efficiency, some terminals store scrollback rows in a compressed format (storing only non-empty cells, or run-length encoding runs of identical cells). This is important for 100K+ line scrollback.

#### 7.2.2 Growable Buffer

A simpler approach: use a `Vec<Row>` that grows indefinitely (or until a memory limit). This is easier to implement but has no upper bound on memory usage:

```rust
struct GrowableScrollback {
    rows: Vec<Row>,
    max_lines: Option<usize>,  // None = unlimited
}

impl GrowableScrollback {
    fn push(&mut self, row: Row) {
        self.rows.push(row);
        if let Some(max) = self.max_lines {
            if self.rows.len() > max {
                // Remove oldest rows in bulk (amortized O(1))
                let excess = self.rows.len() - max;
                self.rows.drain(0..excess);
            }
        }
    }
}
```

The `drain()` operation is O(n) because it shifts elements, but if done in bulk (e.g., when excess exceeds 1000), the amortized cost is low.

### 7.3 Alternate Screen Buffer

Many full-screen applications (vim, less, tmux, htop, man) switch to the **alternate screen buffer** when they start and switch back to the **primary screen buffer** when they exit. This is why your previous terminal output reappears when you quit vim.

The relevant escape sequences:

| Sequence | Action |
|---|---|
| `ESC[?1049h` | Save cursor position, switch to alternate screen, clear it |
| `ESC[?1049l` | Switch back to primary screen, restore cursor position |
| `ESC[?47h` | Switch to alternate screen (older, no cursor save) |
| `ESC[?47l` | Switch back to primary screen |
| `ESC[?1047h` | Switch to alternate screen and clear it |
| `ESC[?1047l` | Switch back, clear alternate screen |

Implementation: maintain two grid buffers and a flag indicating which is active:

```rust
struct Terminal {
    primary: Grid,
    alternate: Grid,
    active_screen: ScreenType,

    // Saved cursor for alternate screen switch
    saved_cursor: Option<CursorState>,
}

enum ScreenType { Primary, Alternate }

impl Terminal {
    fn switch_to_alternate(&mut self) {
        self.saved_cursor = Some(self.cursor_state());
        self.active_screen = ScreenType::Alternate;
        self.alternate.clear();
    }

    fn switch_to_primary(&mut self) {
        self.active_screen = ScreenType::Primary;
        if let Some(cursor) = self.saved_cursor.take() {
            self.restore_cursor(cursor);
        }
    }

    fn active_grid(&self) -> &Grid {
        match self.active_screen {
            ScreenType::Primary => &self.primary,
            ScreenType::Alternate => &self.alternate,
        }
    }

    fn active_grid_mut(&mut self) -> &mut Grid {
        match self.active_screen {
            ScreenType::Primary => &mut self.primary,
            ScreenType::Alternate => &mut self.alternate,
        }
    }
}
```

**Key behavior:** The alternate screen has **no scrollback**. Text that scrolls off the alternate screen is lost. This is intentional--vim's output should not fill your scrollback buffer. The primary screen retains its scrollback. When switching from alternate back to primary, the primary screen's content is exactly as it was before the switch.

### 7.4 Unicode

Unicode handling is the most subtle and error-prone aspect of terminal grid management. Characters that appear as a single visual unit may be composed of multiple Unicode code points, and characters may occupy one or two cells.

#### 7.4.1 Grapheme Clusters

A grapheme cluster is the user-perceived "character." It may consist of one or more Unicode code points:

| Visual | Code Points | Code Point Count | Cell Width |
|---|---|---|---|
| `A` | U+0041 | 1 | 1 |
| `e` | U+0065 U+0301 (e + combining acute) | 2 | 1 |
| `n` | U+006E U+0303 (n + combining tilde) | 2 | 1 |
| `g` | U+0067 U+0308 U+0304 (g + diaeresis + macron) | 3 | 1 |

Your terminal must:
1. Identify grapheme cluster boundaries (use the Unicode `Grapheme_Cluster_Break` property or a library like `unicode-segmentation` in Rust).
2. Store the entire grapheme cluster in a single cell (the base character plus combining marks).
3. Display the combined glyph, not the individual code points.

```rust
use unicode_segmentation::UnicodeSegmentation;

fn process_text(text: &str, grid: &mut Grid, cursor: &mut Cursor) {
    for grapheme in text.graphemes(true) {
        let chars: Vec<char> = grapheme.chars().collect();
        let width = unicode_width::UnicodeWidthStr::width(grapheme);

        if width == 0 {
            // Zero-width character (combining mark applied to previous cell)
            if cursor.col > 0 {
                let prev_col = cursor.col - 1;
                grid.cell_mut(cursor.row, prev_col)
                    .extra_codepoints
                    .extend(chars.iter());
            }
        } else {
            // Normal or wide character
            let cell = grid.cell_mut(cursor.row, cursor.col);
            cell.character = chars[0];
            cell.extra_codepoints.clear();
            cell.extra_codepoints.extend(chars[1..].iter());
            cell.flags.remove(CellFlags::WIDE | CellFlags::WIDE_CONT);

            if width == 2 {
                // Wide character: mark this cell and the next
                cell.flags.insert(CellFlags::WIDE);
                cursor.col += 1;
                if cursor.col < grid.cols {
                    let cont = grid.cell_mut(cursor.row, cursor.col);
                    cont.character = ' ';
                    cont.flags.insert(CellFlags::WIDE_CONT);
                }
            }

            cursor.col += 1;
        }
    }
}
```

#### 7.4.2 Wide Characters (CJK)

CJK (Chinese, Japanese, Korean) characters and some other Unicode characters occupy **two cells** in a terminal grid. The `East_Asian_Width` Unicode property determines width:

| Property Value | Width | Examples |
|---|---|---|
| Narrow (Na), Neutral (N) | 1 cell | Latin, Cyrillic, Greek |
| Halfwidth (H) | 1 cell | Halfwidth Katakana |
| Wide (W) | 2 cells | CJK Ideographs, Hiragana, Katakana |
| Fullwidth (F) | 2 cells | Fullwidth Latin, Fullwidth Digits |
| Ambiguous (A) | 1 or 2 cells (configurable) | Certain Greek, Cyrillic, symbols |

In Rust, use the `unicode-width` crate:

```rust
use unicode_width::UnicodeWidthChar;

let width = UnicodeWidthChar::width('A').unwrap_or(1);   // 1
let width = UnicodeWidthChar::width('\u{4E16}').unwrap_or(1);  // 2 (CJK: "world")
let width = UnicodeWidthChar::width('\u{FF21}').unwrap_or(1);  // 2 (Fullwidth 'A')
```

In C, use `wcwidth()`:

```c
#include <wchar.h>

int w = wcwidth(L'A');        // 1
int w = wcwidth(L'\u4E16');   // 2
int w = wcwidth(L'\u0301');   // 0 (combining mark)
```

**The ambiguous width problem:** Characters with `East_Asian_Width = Ambiguous` may be 1 or 2 cells depending on context. CJK locales traditionally render them as 2 cells; Western locales render them as 1 cell. Most terminals default to 1 cell and allow configuration. This is a genuine unsolved problem in terminal emulation.

#### 7.4.3 Emoji and ZWJ Sequences

Modern emoji present the most challenging Unicode width problem for terminals:

| Emoji | Code Points | Sequence Type | Ideal Width |
|---|---|---|---|
| :) | U+1F600 | Single code point | 2 cells |
| :flag_us: | U+1F1FA U+1F1F8 | Regional indicator pair | 2 cells |
| :family_man_woman_girl_boy: | U+1F468 U+200D U+1F469 U+200D U+1F467 U+200D U+1F466 | ZWJ sequence (7 code points) | 2 cells |
| :woman_tone3: | U+1F469 U+1F3FD | Emoji modifier sequence | 2 cells |
| :rainbow_flag: | U+1F3F3 U+FE0F U+200D U+1F308 | ZWJ with VS16 | 2 cells |

ZWJ (Zero Width Joiner, U+200D) sequences combine multiple emoji into a single glyph. A family emoji can be 7+ code points but should display as a single 2-cell-wide glyph.

The challenge: `wcwidth()` and `unicode-width` do not handle ZWJ sequences correctly because they operate on individual code points, not grapheme clusters. The only reliable way to determine the display width of an emoji ZWJ sequence is to shape it with HarfBuzz (or CoreText) and measure the resulting glyph width.

Most terminals take a pragmatic approach:
- Single emoji code points: 2 cells.
- VS16 (U+FE0F, emoji presentation selector): Forces 2-cell width.
- ZWJ sequences: Render as 2 cells and hope the font handles it.
- Fall back to showing component emoji if the font does not support the ZWJ sequence.

This is an active area of development. The Unicode Consortium publishes `emoji-test.txt` with the full list of recommended emoji sequences.

### 7.5 Bidirectional Text

Bidirectional (bidi) text--mixing left-to-right (Latin) and right-to-left (Arabic, Hebrew) text on the same line--is the most complex text rendering problem in terminals. The Unicode Bidirectional Algorithm (UBA, UAX #9) defines how to reorder characters for display.

**The problem for terminals:** The terminal grid is column-addressed. Escape sequences like `ESC[10G` (move cursor to column 10) assume a left-to-right layout. If characters are reordered by the bidi algorithm, the visual column does not match the logical column. Programs that use cursor addressing (vim, tmux) break.

**Current state of support:**
- **iTerm2:** Experimental bidi support (opt-in). Reorders characters for display but maintains logical column positions internally.
- **mlterm:** The most complete bidi implementation in any terminal.
- **Most terminals (Alacritty, Ghostty, Windows Terminal):** No bidi support. Characters are displayed in the order received (logical order), which is incorrect for RTL text but preserves cursor addressing.
- **ECMA TR/53:** A technical report proposing a standard for bidi in terminals. Not widely implemented.

**Recommendation for a new terminal:** Do not implement bidi in your first version. It requires changes throughout the stack (grid, parser, renderer, input, cursor) and interacts with escape sequences in complex ways. Add it as a later feature if your user base needs it.

**If you do implement bidi:**
1. Apply the UBA to each line of the grid for display purposes only.
2. Maintain a mapping between visual columns and logical columns.
3. Cursor movement sequences operate on logical columns.
4. The renderer displays characters in visual order (after bidi reordering).
5. Selection and clipboard operations must convert between visual and logical positions.

This is equivalent to adding a full bidi layout engine to your terminal, which is thousands of lines of code. Libraries like ICU (`ubidi.h`) or `unicode-bidi` (Rust) implement the UBA.

---

*This concludes Parts I and II. Part III will cover Input Handling and Keyboard Encoding, Part IV will cover Cross-Platform Windowing and Integration, and Part V will cover Advanced Topics (multiplexing, shell integration, performance optimization, and testing).*
