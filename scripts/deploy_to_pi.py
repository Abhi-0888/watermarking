"""
scripts/deploy_to_pi.py
Full automated deployment to the Raspberry Pi using paramiko.
Handles password auth, file transfer, remote setup, and verification.

Run from project root:
    E:\\python.exe scripts/deploy_to_pi.py
"""

import sys, os, stat, time, io, posixpath, tarfile, socket
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vendor'))

import paramiko

# ── Config ────────────────────────────────────────────────────────────────────
PI_HOST     = "10.1.14.11"
PI_PORT     = 22
PI_USER     = "fun"
PI_PASS     = "fun123"
PI_DIR      = "/home/fun/SecureDocSystem"
LOCAL_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PUB_KEY_PATH = os.path.join(os.path.expanduser("~"), ".ssh", "id_rsa_pi_securedoc.pub")

SEP = "=" * 62

def log(msg):   print(f"  {msg}")
def banner(t):  print(f"\n{SEP}\n  {t}\n{SEP}")
def ok(msg):    print(f"  ✓  {msg}")
def fail(msg):  print(f"  ✗  {msg}"); sys.exit(1)


# ── SSH helpers ───────────────────────────────────────────────────────────────

def connect():
    banner("Connecting to Pi")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(PI_HOST, port=PI_PORT, username=PI_USER, password=PI_PASS,
                   timeout=15, look_for_keys=False, allow_agent=False)
    ok(f"SSH connected to {PI_USER}@{PI_HOST}")
    return client


def run(client, cmd, check=True, timeout=120):
    """Run a command, stream output, return (exit_code, stdout, stderr)."""
    print(f"\n  $ {cmd[:120]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out_lines = []
    for line in iter(stdout.readline, ""):
        line = line.rstrip('\n')
        if line:
            print(f"    {line}")
            out_lines.append(line)
    exit_code = stdout.channel.recv_exit_status()
    if check and exit_code != 0:
        err = stderr.read().decode(errors='replace').strip()
        print(f"  ERROR exit {exit_code}: {err}")
        # Don't sys.exit — let caller decide
    return exit_code, '\n'.join(out_lines), ''


def put_file(sftp, local_path, remote_path):
    """Upload one file, creating remote parent dirs as needed."""
    remote_dir = posixpath.dirname(remote_path)
    _sftp_makedirs(sftp, remote_dir)
    sftp.put(local_path, remote_path)


def _sftp_makedirs(sftp, remote_dir):
    parts = remote_dir.split('/')
    path = ''
    for part in parts:
        if not part:
            path = '/'
            continue
        path = posixpath.join(path, part)
        try:
            sftp.stat(path)
        except FileNotFoundError:
            try:
                sftp.mkdir(path)
            except Exception:
                pass


def put_dir(sftp, local_dir, remote_dir, skip_patterns=None):
    """Recursively upload a local directory."""
    skip_patterns = skip_patterns or []
    for root, dirs, files in os.walk(local_dir):
        # Skip unwanted dirs
        dirs[:] = [d for d in dirs
                   if d not in ('__pycache__', '.git', 'venv', '.venv',
                                'vendor', 'node_modules', 'attacks', 'tampered',
                                'tampered2', 'keys', 'keys2')]
        for fname in files:
            if fname.endswith('.pyc'):
                continue
            if 'private' in fname.lower():
                continue  # never transfer private keys
            local_f  = os.path.join(root, fname)
            rel      = os.path.relpath(local_f, local_dir).replace('\\', '/')
            remote_f = posixpath.join(remote_dir, rel)
            _sftp_makedirs(sftp, posixpath.dirname(remote_f))
            sftp.put(local_f, remote_f)
            print(f"    -> {rel}")


# ── Stage 1: Authorize SSH key so future connections are passwordless ─────────

def authorize_ssh_key(client, sftp):
    banner("Stage 1 — Authorize SSH public key")
    if not os.path.exists(PUB_KEY_PATH):
        log("No public key found — skipping key auth setup")
        return
    with open(PUB_KEY_PATH) as f:
        pub_key = f.read().strip()

    run(client, "mkdir -p ~/.ssh && chmod 700 ~/.ssh", check=False)
    # Append key only if not already present
    check_cmd = f"grep -qF '{pub_key}' ~/.ssh/authorized_keys 2>/dev/null"
    code, _, _ = run(client, check_cmd, check=False)
    if code != 0:
        run(client, f"echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")
        ok("Public key added to authorized_keys")
    else:
        ok("Public key already authorized")


# ── Stage 2: Fix apt packages (libatlas-base-dev not available → use libopenblas-dev) ──

def install_system_packages(client):
    banner("Stage 2 — System packages")

    # Detect OS to pick right packages
    code, out, _ = run(client, "lsb_release -cs 2>/dev/null || cat /etc/os-release | grep VERSION_CODENAME | cut -d= -f2", check=False)
    codename = out.strip().split('\n')[-1].lower()
    log(f"OS codename: {codename}")

    # libatlas-base-dev not available on bookworm — use libopenblas-dev instead
    run(client, "sudo apt-get update -qq", timeout=120)

    pkgs = "python3-pip python3-venv python3-numpy git"
    # Try opencv system package first (fastest)
    code, _, _ = run(client, f"sudo apt-get install -y {pkgs} python3-opencv libopenblas-dev", check=False, timeout=300)
    if code != 0:
        log("python3-opencv not available via apt, will install via pip")
        run(client, f"sudo apt-get install -y {pkgs} libopenblas-dev", timeout=300)
    ok("System packages installed")


# ── Stage 3: Transfer project files ──────────────────────────────────────────

def transfer_files(client):
    banner("Stage 3 — File transfer")
    sftp = client.open_sftp()

    # Ensure base dirs exist
    for d in [PI_DIR,
              PI_DIR+"/samples",
              PI_DIR+"/results",
              PI_DIR+"/samples/tampered",
              PI_DIR+"/samples/tampered2"]:
        _sftp_makedirs(sftp, d)

    # Source code directories
    for src_dir in ['encryption','watermark','verification','provenance',
                    'utils','raspberry_pi','scripts','docs']:
        local = os.path.join(LOCAL_ROOT, src_dir)
        if os.path.isdir(local):
            log(f"Uploading {src_dir}/")
            put_dir(sftp, local, f"{PI_DIR}/{src_dir}")

    # Root-level files
    root_files = ['main.py','transfer.py','requirements.txt',
                  'README.md','ADDITIONS.md','DEPLOYMENT.md','.gitignore']
    for f in root_files:
        lp = os.path.join(LOCAL_ROOT, f)
        if os.path.exists(lp):
            log(f"Uploading {f}")
            sftp.put(lp, f"{PI_DIR}/{f}")

    # Sample files (no private keys, no venv)
    sample_files = [
        "samples/input.png",
        "samples/input1.png",
        "samples/watermarked.png",
        "samples/watermarked2.png",
        "samples/watermarked_v2.png",
        "samples/watermarked_v3.png",
        "samples/watermarked2_v2.png",
        "samples/watermarked2_v3.png",
        "samples/manifest.json",
        "samples/manifest2.json",
        "samples/manifest_v2.json",
        "samples/manifest_v3.json",
        "samples/manifest2_v2.json",
        "samples/manifest2_v3.json",
        "samples/registry.json",
        "samples/registry2.json",
        "samples/provenance.json",
        "samples/provenance2.json",
    ]
    log("Uploading sample files...")
    for rel in sample_files:
        lp = os.path.join(LOCAL_ROOT, rel)
        if os.path.exists(lp):
            rp = f"{PI_DIR}/{rel}"
            _sftp_makedirs(sftp, posixpath.dirname(rp))
            sftp.put(lp, rp)
            print(f"    -> {rel}")
        else:
            print(f"    (skip, not found) {rel}")

    sftp.close()
    ok("All files transferred")


# ── Stage 4: Python venv + pip + GPIO ─────────────────────────────────────────

def setup_python_env(client):
    banner("Stage 4 — Python environment")

    run(client, f"cd {PI_DIR} && python3 -m venv --system-site-packages venv", timeout=60)

    pip = f"{PI_DIR}/venv/bin/pip"
    run(client, f"{pip} install --quiet --upgrade pip", timeout=60)
    run(client, f"{pip} install --quiet -r {PI_DIR}/requirements.txt", timeout=300)
    run(client, f"{pip} install --quiet psutil", timeout=60)

    # GPIO library
    run(client, f"bash {PI_DIR}/raspberry_pi/install_gpio.sh", check=False, timeout=120)

    # Confirm imports
    banner("Import check")
    run(client,
        f"{PI_DIR}/venv/bin/python3 -c \""
        "import cv2, numpy; from Crypto.PublicKey import RSA; "
        "print('opencv:', cv2.__version__); "
        "print('numpy:', numpy.__version__); "
        "print('pycryptodome: OK'); "
        "import subprocess, sys; "
        "r=subprocess.run(['cat','/proc/device-tree/model'],capture_output=True); "
        "print('Pi model:', r.stdout.decode(errors=\\'replace\\').strip());"
        "\"",
        timeout=30)


# ── Stage 5: Live verification on Pi ─────────────────────────────────────────

def verify_on_pi(client):
    banner("Stage 5 — Live verification on Pi (DOC-2026-001, input.png)")
    py = f"{PI_DIR}/venv/bin/python3"
    cmd = (
        f"cd {PI_DIR} && PYTHONIOENCODING=utf-8 {py} "
        f"raspberry_pi/pi_verify_terminal.py "
        f"--file samples/watermarked.png "
        f"--manifest samples/manifest.json "
        f"--registry samples/registry.json "
        f"--provenance samples/provenance.json "
        f"--mode online --no-led"
    )
    run(client, cmd, timeout=60)

    banner("Stage 5b — Live verification on Pi (DOC-2026-002, input1.jpg)")
    cmd2 = (
        f"cd {PI_DIR} && PYTHONIOENCODING=utf-8 {py} "
        f"raspberry_pi/pi_verify_terminal.py "
        f"--file samples/watermarked2.png "
        f"--manifest samples/manifest2.json "
        f"--registry samples/registry2.json "
        f"--provenance samples/provenance2.json "
        f"--mode online --no-led"
    )
    run(client, cmd2, timeout=60)


# ── Stage 6: LED test (hardware check) ───────────────────────────────────────

def led_test(client):
    banner("Stage 6 — LED test (GPIO hardware)")
    py = f"{PI_DIR}/venv/bin/python3"
    run(client,
        f"cd {PI_DIR} && PYTHONIOENCODING=utf-8 {py} raspberry_pi/led_test.py",
        check=False, timeout=20)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(SEP)
    print("  SecureDocSystem → Pi Deployment")
    print(f"  Target : {PI_USER}@{PI_HOST}:{PI_DIR}")
    print(SEP)

    client = connect()

    try:
        authorize_ssh_key(client, client.open_sftp())
        install_system_packages(client)
        transfer_files(client)
        setup_python_env(client)
        verify_on_pi(client)
        led_test(client)
    finally:
        client.close()

    banner("DEPLOYMENT COMPLETE")
    print(f"""
  SSH into Pi anytime:
    ssh {PI_USER}@{PI_HOST}

  Run full demo on Pi:
    ssh {PI_USER}@{PI_HOST} "cd {PI_DIR} && source venv/bin/activate && python3 scripts/pi_demo.py --skip-issue --no-led"

  Run with GPIO LEDs:
    ssh {PI_USER}@{PI_HOST} "cd {PI_DIR} && source venv/bin/activate && python3 scripts/pi_demo.py --skip-issue"

  Benchmark:
    ssh {PI_USER}@{PI_HOST} "cd {PI_DIR} && source venv/bin/activate && python3 raspberry_pi/benchmark.py --file samples/watermarked.png --manifest samples/manifest.json --provenance samples/provenance.json -n 30"
""")


if __name__ == "__main__":
    main()
