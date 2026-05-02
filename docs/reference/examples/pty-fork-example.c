/**
 * PTY Fork Example — Terminal Emulator Shell Connection
 * =====================================================
 * Demonstrates how to create a PTY, fork a child process,
 * and establish bidirectional communication with a shell.
 *
 * Works on: Linux, macOS
 * Compile:  gcc -o pty-example pty-fork-example.c -lutil
 * Run:      ./pty-example
 *
 * Press Ctrl+D to exit.
 */

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

#if defined(__APPLE__)
#include <util.h>  /* macOS: openpty(), forkpty() in util.h */
#elif defined(__linux__)
#include <pty.h>   /* Linux: openpty(), forkpty() in pty.h */
#endif

static struct termios orig_termios;
static int master_fd = -1;

/* Restore terminal on exit */
void cleanup(void) {
    if (master_fd >= 0)
        close(master_fd);
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
}

/* Handle SIGWINCH (terminal resize) */
void handle_sigwinch(int sig) {
    (void)sig;
    struct winsize ws;
    if (ioctl(STDIN_FILENO, TIOCGWINSZ, &ws) == 0) {
        ioctl(master_fd, TIOCSWINSZ, &ws);
    }
}

/* Handle SIGCHLD (child process exit) */
void handle_sigchld(int sig) {
    (void)sig;
    int status;
    waitpid(-1, &status, WNOHANG);
}

int main(void) {
    pid_t pid;
    struct winsize ws;
    char buf[4096];

    /* Save original terminal attributes */
    tcgetattr(STDIN_FILENO, &orig_termios);
    atexit(cleanup);

    /* Get current window size */
    ioctl(STDIN_FILENO, TIOCGWINSZ, &ws);

    /* Fork with PTY — child gets slave, parent gets master */
    pid = forkpty(&master_fd, NULL, NULL, &ws);

    if (pid < 0) {
        perror("forkpty");
        return 1;
    }

    if (pid == 0) {
        /* === CHILD PROCESS === */
        /* The slave PTY is already connected to stdin/stdout/stderr */

        /* Set up environment */
        setenv("TERM", "xterm-256color", 1);

        /* Execute the user's shell */
        const char *shell = getenv("SHELL");
        if (!shell) shell = "/bin/bash";

        execlp(shell, shell, (char *)NULL);
        perror("execlp");  /* Only reached if exec fails */
        _exit(1);
    }

    /* === PARENT PROCESS (Terminal Emulator) === */

    /* Set up signal handlers */
    signal(SIGWINCH, handle_sigwinch);
    signal(SIGCHLD, handle_sigchld);

    /* Put terminal in raw mode */
    struct termios raw = orig_termios;
    raw.c_lflag &= ~(ECHO | ICANON | ISIG | IEXTEN);
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_cc[VMIN] = 1;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);

    /* Make master_fd non-blocking */
    fcntl(master_fd, F_SETFL, fcntl(master_fd, F_GETFL) | O_NONBLOCK);

    /* Main I/O loop */
    fd_set read_fds;
    int max_fd = (master_fd > STDIN_FILENO) ? master_fd : STDIN_FILENO;

    for (;;) {
        FD_ZERO(&read_fds);
        FD_SET(STDIN_FILENO, &read_fds);
        FD_SET(master_fd, &read_fds);

        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            if (errno == EINTR) continue;  /* Signal interrupted */
            break;
        }

        /* Data from shell → write to our stdout (display) */
        if (FD_ISSET(master_fd, &read_fds)) {
            ssize_t n = read(master_fd, buf, sizeof(buf));
            if (n <= 0) break;  /* Shell exited or error */
            write(STDOUT_FILENO, buf, n);
        }

        /* Data from keyboard → write to master PTY (send to shell) */
        if (FD_ISSET(STDIN_FILENO, &read_fds)) {
            ssize_t n = read(STDIN_FILENO, buf, sizeof(buf));
            if (n <= 0) break;
            write(master_fd, buf, n);
        }
    }

    return 0;
}
