//! # Terminal Emulator Skeleton (Rust)
//!
//! Cross-platform terminal emulator skeleton demonstrating:
//! - PTY creation via `portable-pty` (Linux, macOS, Windows ConPTY)
//! - VT100 escape code parsing via `vte`
//! - Raw terminal I/O via `crossterm`
//!
//! ## Run
//! ```
//! cargo run
//! ```
//!
//! Press Ctrl+D to exit.

use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use std::io::{Read, Write};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use vte::{Params, Parser, Perform};

/// VT100 Parser Event Handler
///
/// In a real terminal emulator, this would update a grid buffer.
/// Here we just demonstrate the parsing pipeline.
struct TerminalHandler {
    /// Current foreground color (SGR state)
    fg_color: Option<u8>,
    /// Character count for statistics
    char_count: u64,
    /// Escape sequence count
    esc_count: u64,
}

impl TerminalHandler {
    fn new() -> Self {
        Self {
            fg_color: None,
            char_count: 0,
            esc_count: 0,
        }
    }
}

impl Perform for TerminalHandler {
    /// Called for each printable character
    fn print(&mut self, c: char) {
        self.char_count += 1;
        // In a real terminal: grid[cursor_row][cursor_col].character = c;
        print!("{}", c);
    }

    /// Called for each C0/C1 control character (e.g., \n, \r, \t, BEL)
    fn execute(&mut self, byte: u8) {
        match byte {
            0x07 => {} // BEL — would ring bell
            0x08 => print!("\x08"), // BS — backspace
            0x09 => print!("\t"),   // HT — horizontal tab
            0x0A => print!("\n"),   // LF — line feed
            0x0D => print!("\r"),   // CR — carriage return
            _ => {}
        }
    }

    /// Called when a CSI sequence is complete (e.g., ESC[31m, ESC[2J)
    fn csi_dispatch(&mut self, params: &Params, _intermediates: &[u8], _ignore: bool, action: char) {
        self.esc_count += 1;

        match action {
            // SGR — Select Graphic Rendition (colors, bold, etc.)
            'm' => {
                // Note: SGR params can be semicolon-separated (38;5;N) or
                // colon-separated (38:5:N). vte's Params.iter() yields
                // subparameter groups. We flatten for semicolon-separated
                // (the common case) and also handle colon-separated.
                let flat: Vec<u16> = params.iter()
                    .flat_map(|sub| sub.iter().copied())
                    .collect();
                let mut i = 0;
                while i < flat.len() {
                    match flat[i] {
                        0 => { self.fg_color = None; }           // Reset
                        1 => {}                                    // Bold
                        30..=37 => { self.fg_color = Some(flat[i] as u8 - 30); }
                        38 => {
                            // 256-color (38;5;N) or true color (38;2;R;G;B)
                            if i + 2 < flat.len() && flat[i + 1] == 5 {
                                self.fg_color = Some(flat[i + 2] as u8);
                                i += 2; // skip 5 and N
                            } else if i + 4 < flat.len() && flat[i + 1] == 2 {
                                // 24-bit: flat[i+2]=R, flat[i+3]=G, flat[i+4]=B
                                i += 4; // skip 2, R, G, B
                            }
                        }
                        _ => {}
                    }
                    i += 1;
                }
            }
            // CUP — Cursor Position (ESC[row;colH)
            'H' | 'f' => {
                // In a real terminal: move cursor to (row, col)
            }
            // ED — Erase in Display (ESC[2J = clear screen)
            'J' => {}
            // EL — Erase in Line
            'K' => {}
            // CUU/CUD/CUF/CUB — Cursor movement
            'A' | 'B' | 'C' | 'D' => {}
            _ => {}
        }

        // Pass through to real terminal for visual output
        print!("\x1b[");
        let param_strs: Vec<String> = params.iter().map(|p| {
            p.iter().map(|v| v.to_string()).collect::<Vec<_>>().join(":")
        }).collect();
        print!("{}{}", param_strs.join(";"), action);
    }

    /// Called when an OSC sequence is complete (e.g., ESC]0;title BEL)
    fn osc_dispatch(&mut self, params: &[&[u8]], _bell_terminated: bool) {
        self.esc_count += 1;
        if let Some(first) = params.first() {
            match *first {
                b"0" | b"2" => {
                    // Set window title
                    if let Some(title) = params.get(1) {
                        let title = String::from_utf8_lossy(title);
                        // In a real terminal: window.set_title(&title);
                        log::debug!("Title: {}", title);
                    }
                }
                _ => {}
            }
        }
    }

    /// Called for ESC sequences that aren't CSI/OSC
    fn esc_dispatch(&mut self, _intermediates: &[u8], _ignore: bool, _byte: u8) {
        self.esc_count += 1;
    }

    fn hook(&mut self, _params: &Params, _intermediates: &[u8], _ignore: bool, _action: char) {}
    fn put(&mut self, _byte: u8) {}
    fn unhook(&mut self) {}
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();

    println!("=== Terminal Emulator Skeleton (Rust) ===");
    println!("Using: portable-pty + vte");
    println!("Press Ctrl+D to exit.\n");

    // 1. Create PTY system (auto-detects platform)
    let pty_system = native_pty_system();

    // 2. Open a PTY pair with initial size
    let pair = pty_system.openpty(PtySize {
        rows: 24,
        cols: 80,
        pixel_width: 0,
        pixel_height: 0,
    })?;

    // 3. Spawn the user's shell in the PTY
    let mut cmd = CommandBuilder::new_default_prog();
    cmd.env("TERM", "xterm-256color");
    let _child = pair.slave.spawn_command(cmd)?;

    // Drop slave — the child process owns it now
    drop(pair.slave);

    // 4. Get reader/writer for the master side
    let mut reader = pair.master.try_clone_reader()?;
    let writer = Arc::new(Mutex::new(pair.master));

    // 5. Create VT100 parser and handler
    let handler = Arc::new(Mutex::new(TerminalHandler::new()));
    let parser = Arc::new(Mutex::new(Parser::new()));

    // 6. Enable raw mode for our terminal
    crossterm::terminal::enable_raw_mode()?;

    // 7. Thread: Read from PTY master → parse → display
    let handler_clone = Arc::clone(&handler);
    let parser_clone = Arc::clone(&parser);
    let reader_thread = thread::spawn(move || {
        let mut buf = [0u8; 4096];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => break, // EOF — shell exited
                Ok(n) => {
                    let mut h = handler_clone.lock().unwrap();
                    let mut p = parser_clone.lock().unwrap();
                    for byte in &buf[..n] {
                        p.advance(&mut *h, *byte);
                    }
                    let _ = std::io::stdout().flush();
                }
                Err(_) => break,
            }
        }
    });

    // 8. Thread: Read from stdin → write to PTY master
    let writer_clone = Arc::clone(&writer);
    let stdin_thread = thread::spawn(move || {
        let mut buf = [0u8; 256];
        loop {
            match std::io::stdin().read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    if let Ok(mut w) = writer_clone.lock() {
                        let _ = w.write_all(&buf[..n]);
                    }
                }
                Err(_) => break,
            }
        }
    });

    // 9. Wait for either thread to finish
    let _ = reader_thread.join();

    // Small delay to let output flush
    thread::sleep(Duration::from_millis(100));

    // 10. Restore terminal and print stats
    crossterm::terminal::disable_raw_mode()?;

    let h = handler.lock().unwrap();
    println!("\n\n=== Session Statistics ===");
    println!("Characters printed: {}", h.char_count);
    println!("Escape sequences:   {}", h.esc_count);

    // stdin_thread will exit when stdin closes or PTY writer drops
    // Note: join() would block, so we just let it detach gracefully
    let _ = stdin_thread.join();

    Ok(())
}
