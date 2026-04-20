import html
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from verification.verify import verify_document


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Secure Document Web Verifier</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; background: #f4f7fb; color: #1a2333; }}
    .card {{ background: white; border-radius: 12px; padding: 24px; max-width: 960px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
    h1 {{ margin-top: 0; }}
    label {{ display: block; margin-top: 14px; font-weight: 600; }}
    input, select {{ margin-top: 6px; padding: 8px; width: 100%; max-width: 100%; box-sizing: border-box; }}
    button {{ margin-top: 18px; padding: 10px 16px; }}
    pre {{ background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 10px; overflow: auto; }}
    .error {{ color: #b91c1c; font-weight: 600; }}
    .hint {{ color: #475569; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Secure Digital Document Web Verifier</h1>
    <p>Enter local file paths for the protected file, manifest, and optional registry, then run verification in your browser.</p>
    <p class="hint">Example protected file: <code>samples\\watermarked.png</code></p>
    <p class="hint">Example manifest file: <code>samples\\manifest.json</code></p>
    <form method="post">
      <label>Protected File Path</label>
      <input type="text" name="protected_file" value="{protected_file}" required>

      <label>Manifest File Path</label>
      <input type="text" name="manifest_file" value="{manifest_file}" required>

      <label>Registry File Path</label>
      <input type="text" name="registry_file" value="{registry_file}">

      <label>Verification Mode</label>
      <select name="mode">
        <option value="offline" {offline_selected}>Offline</option>
        <option value="online" {online_selected}>Online</option>
      </select>

      <button type="submit">Verify Document</button>
    </form>
    {error_block}
    {report_block}
  </div>
</body>
</html>
"""


def _render_page(protected_file="", manifest_file="", registry_file="", mode="offline", report="", error=""):
    error_block = f'<p class="error">{html.escape(error)}</p>' if error else ""
    report_block = f"<h2>Verification Result</h2><pre>{html.escape(report)}</pre>" if report else ""
    return HTML_TEMPLATE.format(
        protected_file=html.escape(protected_file),
        manifest_file=html.escape(manifest_file),
        registry_file=html.escape(registry_file),
        offline_selected="selected" if mode == "offline" else "",
        online_selected="selected" if mode == "online" else "",
        error_block=error_block,
        report_block=report_block,
    ).encode("utf-8")


def _format_report(report):
    lines = [
        f"Mode: {report['mode']}",
        f"Document ID: {report['document_id']}",
        f"Authentic: {report['authentic']}",
        f"Hash Valid: {report['hash_valid']}",
        f"Signature Valid: {report['signature_valid']}",
        f"Watermark Valid: {report['watermark_valid']}",
        f"Registry Valid: {report['registry_valid']}",
        f"Receiver: {report['receiver_identity']}",
        f"Watermark Confidence: {report['watermark_confidence']}",
        f"Watermark Text: {report['watermark_text'] or 'Not recovered'}",
        f"Issues: {', '.join(report['issues']) if report['issues'] else 'None'}",
    ]
    return "\n".join(lines)


class VerifyHandler(BaseHTTPRequestHandler):
    def _send_html(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send_html(_render_page())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="replace")
        form = parse_qs(raw_body)

        protected_file = form.get("protected_file", [""])[0].strip()
        manifest_file = form.get("manifest_file", [""])[0].strip()
        registry_file = form.get("registry_file", [""])[0].strip()
        mode = form.get("mode", ["offline"])[0]

        error = ""
        report_text = ""

        if not protected_file or not manifest_file:
            error = "Protected file path and manifest file path are required."
        elif mode == "online" and not registry_file:
            error = "Registry file path is required for online mode."
        else:
            if not os.path.exists(protected_file):
                error = f"Protected file not found: {protected_file}"
            elif not os.path.exists(manifest_file):
                error = f"Manifest file not found: {manifest_file}"
            elif mode == "online" and not os.path.exists(registry_file):
                error = f"Registry file not found: {registry_file}"
            else:
                try:
                    report = verify_document(
                        protected_file,
                        manifest_file,
                        mode=mode,
                        registry_path=(registry_file or None),
                    )
                    report_text = _format_report(report)
                except Exception as exc:
                    error = str(exc)

        self._send_html(
            _render_page(
                protected_file=protected_file,
                manifest_file=manifest_file,
                registry_file=registry_file,
                mode=mode,
                report=report_text,
                error=error,
            )
        )

    def log_message(self, format, *args):
        return


def main():
    server = HTTPServer(("127.0.0.1", 5000), VerifyHandler)
    print("Secure Document Web Verifier running at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
