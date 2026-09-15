"""
Renders the verification result on the Raspberry Pi's monitor.

Two modes:
  - plain print (default): works over SSH, in a terminal, or piped to a
    log — no extra dependency, always available.
  - curses fullscreen (--fullscreen): takes over the console for a
    kiosk-style HDMI display like the one in the architecture diagram.
    Falls back to plain print automatically if curses isn't usable
    (e.g. no attached terminal).
"""

BOX_WIDTH = 46


def _line(label, value):
    return f"{label:<18}: {value}"


def build_dashboard_lines(report, tamper_report, provenance_entry, traversal_path):
    authentic = report["authentic"]
    status = "AUTHENTIC" if authentic else "TAMPERED"
    tamper_blocks = tamper_report.get("block_labels", []) if tamper_report else []
    tamper_text = "NONE DETECTED" if not tamper_blocks else ", ".join(tamper_blocks[:6])

    lines = [
        "SECURE DOCUMENT MONITOR",
        "-" * BOX_WIDTH,
        _line("DOCUMENT ID", report.get("document_id", "Unknown")),
        _line("STATUS", status),
        _line("CURRENT HOLDER", report.get("receiver_identity") or "Unknown"),
        _line("COPY VERSION", report.get("version") or "Unknown"),
        _line("TRANSFER COUNT", provenance_entry.get("transfer_count") if provenance_entry else "N/A"),
        _line("HASH CHECK", "PASS" if report.get("hash_valid") else "FAIL"),
        _line("SIGNATURE CHECK", "PASS" if report.get("signature_valid") else "FAIL"),
        _line("WATERMARK", "VALID" if report.get("watermark_valid") else "INVALID"),
        _line("TAMPER", tamper_text),
        "-" * BOX_WIDTH,
        "TRAVERSAL PATH:",
        "  " + (" -> ".join(traversal_path) if traversal_path else "Not available"),
        "-" * BOX_WIDTH,
    ]
    return lines


def print_dashboard(report, tamper_report, provenance_entry, traversal_path):
    lines = build_dashboard_lines(report, tamper_report, provenance_entry, traversal_path)
    border = "=" * BOX_WIDTH
    print(border)
    for line in lines:
        print(line)
    print(border)


def show_fullscreen_dashboard(report, tamper_report, provenance_entry, traversal_path, hold_seconds=8):
    """Best-effort curses fullscreen view for an HDMI-attached monitor.
    Silently falls back to print_dashboard if curses can't attach to a tty."""
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
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        color = curses.color_pair(1) if authentic else curses.color_pair(2)

        stdscr.clear()
        stdscr.attron(curses.A_BOLD)
        for row, line in enumerate(lines):
            attr = color if ("STATUS" in line or "TAMPER" in line) else curses.A_NORMAL
            try:
                stdscr.addstr(row + 1, 2, line, attr)
            except curses.error:
                pass  # terminal too small for this line — skip it
        stdscr.attroff(curses.A_BOLD)
        stdscr.refresh()
        time.sleep(hold_seconds)

    try:
        curses.wrapper(_draw)
    except curses.error:
        print_dashboard(report, tamper_report, provenance_entry, traversal_path)
