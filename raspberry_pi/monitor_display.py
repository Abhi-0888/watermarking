"""
Renders the verification result on the Raspberry Pi's monitor.

Two modes:
  - plain print (default): works over SSH, in a terminal, or piped to a
    log — no extra dependency, always available.
  - curses fullscreen (--fullscreen): takes over the console for a
    kiosk-style HDMI display like the one in the architecture diagram.
    Falls back to plain print automatically if curses can't attach to a tty.

Layout fixes (over original):
  - Title row is centre-aligned and highlighted with A_REVERSE so it is
    readable on any terminal colour scheme (dark or light background).
  - All content rows are centre-aligned to the terminal width.
  - STATUS and TAMPER lines are coloured green/red.
  - A "Press any key to dismiss…" footer appears at the bottom.
  - Terminal too small (< 52 cols or < 20 rows) falls back to plain print.
"""

import sys as _sys

# ── Stdout encoding setup ─────────────────────────────────────────────────────
# On the Raspberry Pi (UTF-8 locale) this is a no-op.
# On Windows (cp1252 console) it prevents UnicodeEncodeError when printing
# box-drawing characters.  We reconfigure to UTF-8 with replacement so the
# plain-print dashboard never crashes regardless of the host terminal.
if hasattr(_sys.stdout, "reconfigure"):
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # read-only or already correct — ignore

BOX_WIDTH = 50  # minimum content width; wider terminals will centre it

# Use Unicode box-drawing characters only if stdout can actually encode them
# (after the reconfigure above this will be True on any UTF-8 terminal).
_STDOUT_ENC   = getattr(_sys.stdout, "encoding", "utf-8") or "utf-8"
_USE_UNICODE  = _STDOUT_ENC.lower().replace("-", "") in (
    "utf8", "utf16", "utf32", "utf16le", "utf16be"
)
_SEP_CHAR     = "\u2500" if _USE_UNICODE else "-"   # ─  or -
_BORDER_CHAR  = "\u2550" if _USE_UNICODE else "="   # ═  or =


def _line(label, value):
    return f"{label:<18}: {value}"


def build_dashboard_lines(report, tamper_report, provenance_entry, traversal_path):
    authentic = report["authentic"]
    status = "AUTHENTIC" if authentic else "TAMPERED"
    tamper_blocks = tamper_report.get("block_labels", []) if tamper_report else []
    tamper_text = "NONE DETECTED" if not tamper_blocks else ", ".join(tamper_blocks[:6])

    lines = [
        ("title",  "SECURE DOCUMENT MONITOR"),
        ("sep",    _SEP_CHAR * BOX_WIDTH),
        ("normal", _line("DOCUMENT ID",    report.get("document_id", "Unknown"))),
        ("status", _line("STATUS",         status)),
        ("normal", _line("CURRENT HOLDER", report.get("receiver_identity") or "Unknown")),
        ("normal", _line("COPY VERSION",   report.get("version") or "Unknown")),
        ("normal", _line("TRANSFER COUNT", provenance_entry.get("transfer_count") if provenance_entry else "N/A")),
        ("normal", _line("HASH CHECK",     "PASS" if report.get("hash_valid") else "FAIL")),
        ("normal", _line("SIGNATURE",      "PASS" if report.get("signature_valid") else "FAIL")),
        ("normal", _line("WATERMARK",      "VALID" if report.get("watermark_valid") else "INVALID")),
        ("tamper", _line("TAMPER",         tamper_text)),
        ("sep",    _SEP_CHAR * BOX_WIDTH),
        ("normal", "TRAVERSAL PATH:"),
        ("path",   "  " + (" -> ".join(traversal_path) if traversal_path else "Not available")),
        ("sep",    _SEP_CHAR * BOX_WIDTH),
    ]
    return lines


def print_dashboard(report, tamper_report, provenance_entry, traversal_path):
    """Plain-text output — works over SSH, Windows terminals, and any locale."""
    lines = build_dashboard_lines(report, tamper_report, provenance_entry, traversal_path)
    border = _BORDER_CHAR * BOX_WIDTH
    print(border)
    for _tag, text in lines:
        print(text)
    print(border)


def show_fullscreen_dashboard(report, tamper_report, provenance_entry, traversal_path, hold_seconds=8):
    """Best-effort curses fullscreen view for an HDMI-attached monitor or VNC terminal.
    Silently falls back to print_dashboard if curses can't attach to a tty or the
    terminal is too small."""
    try:
        import curses
        import time
    except ImportError:
        print_dashboard(report, tamper_report, provenance_entry, traversal_path)
        return

    lines = build_dashboard_lines(report, tamper_report, provenance_entry, traversal_path)
    authentic = report["authentic"]

    def _draw(stdscr):
        curses.curs_set(0)
        max_rows, max_cols = stdscr.getmaxyx()

        # Minimum size guard — fall back to plain print if too cramped
        if max_cols < BOX_WIDTH + 2 or max_rows < len(lines) + 4:
            raise curses.error("terminal too small")

        curses.start_color()
        curses.use_default_colors()
        # Colour pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # authentic
        curses.init_pair(2, curses.COLOR_RED,   -1)   # tampered
        curses.init_pair(3, curses.COLOR_CYAN,  -1)   # path / info
        curses.init_pair(4, curses.COLOR_WHITE, -1)   # normal

        ok_color     = curses.color_pair(1) | curses.A_BOLD
        bad_color    = curses.color_pair(2) | curses.A_BOLD
        path_color   = curses.color_pair(3)
        normal_attr  = curses.A_NORMAL
        title_attr   = curses.A_REVERSE | curses.A_BOLD
        sep_attr     = curses.A_DIM

        verdict_color = ok_color if authentic else bad_color

        # Horizontal padding so content block is centred
        left_pad = max(0, (max_cols - BOX_WIDTH) // 2)

        stdscr.clear()

        # Top border
        border = "═" * min(BOX_WIDTH, max_cols - left_pad - 1)
        row = 1
        try:
            stdscr.addstr(row, left_pad, border, verdict_color)
        except curses.error:
            pass
        row += 1

        for tag, text in lines:
            if row >= max_rows - 2:
                break
            # Truncate line if it overflows the terminal width
            max_text = max_cols - left_pad - 1
            display = text[:max_text] if len(text) > max_text else text

            if tag == "title":
                attr = title_attr | (ok_color if authentic else bad_color)
                # Centre the title within BOX_WIDTH
                centred = display.center(min(BOX_WIDTH, max_cols - left_pad - 1))
                try:
                    stdscr.addstr(row, left_pad, centred, attr)
                except curses.error:
                    pass
            elif tag == "sep":
                try:
                    stdscr.addstr(row, left_pad, display, sep_attr)
                except curses.error:
                    pass
            elif tag == "status":
                try:
                    stdscr.addstr(row, left_pad, display, verdict_color)
                except curses.error:
                    pass
            elif tag == "tamper":
                attr = bad_color if report.get("tamper_localization", {}).get("tampered") else ok_color
                try:
                    stdscr.addstr(row, left_pad, display, attr)
                except curses.error:
                    pass
            elif tag == "path":
                try:
                    stdscr.addstr(row, left_pad, display, path_color)
                except curses.error:
                    pass
            else:
                try:
                    stdscr.addstr(row, left_pad, display, normal_attr)
                except curses.error:
                    pass
            row += 1

        # Bottom border
        try:
            stdscr.addstr(row, left_pad, border, verdict_color)
        except curses.error:
            pass
        row += 1

        # Footer — press any key
        footer = "[ Press any key to dismiss ]"
        footer_col = max(0, (max_cols - len(footer)) // 2)
        try:
            stdscr.addstr(max_rows - 1, footer_col, footer, curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

        # Wait for keypress OR timeout, whichever comes first
        stdscr.nodelay(False)
        stdscr.timeout(hold_seconds * 1000)
        stdscr.getch()

    try:
        curses.wrapper(_draw)
    except curses.error:
        # Terminal too small or no TTY — fall back gracefully
        print_dashboard(report, tamper_report, provenance_entry, traversal_path)
