"""
raspberry_pi/pi_deploy_config.py
Central configuration for the real Raspberry Pi at 10.1.14.11.

Import this wherever you need Pi connection details rather than
scattering literals across multiple scripts.

Usage:
    from raspberry_pi.pi_deploy_config import PI
    print(PI.host)          # 10.1.14.11
    print(PI.ssh_user)      # fun
    print(PI.project_dir)   # /home/fun/SecureDocSystem
"""

from dataclasses import dataclass, field
from pathlib import Path
import sys

# ── Local project root ────────────────────────────────────────────────────────
LOCAL_ROOT = Path(__file__).resolve().parent.parent   # d:/.../SecureDocSystem


@dataclass
class PiConfig:
    # ── Network ───────────────────────────────────────────────────────────────
    host: str       = "10.1.14.11"
    ssh_port: int   = 22
    vnc_port: int   = 5900

    # ── SSH credentials ───────────────────────────────────────────────────────
    # Username provided by the Pi owner.
    # Catchphrase (RealVNC): "Audio neon fossil. Ticket Gong Ringo."
    # Signature:             5d-73-2e-ae-7e-cd-fe-62
    ssh_user: str   = "fun"

    # ── Remote paths ──────────────────────────────────────────────────────────
    home_dir:     str = "/home/fun"
    project_dir:  str = "/home/fun/SecureDocSystem"
    venv_python:  str = "/home/fun/SecureDocSystem/venv/bin/python3"
    venv_activate:str = "/home/fun/SecureDocSystem/venv/bin/activate"
    samples_dir:  str = "/home/fun/SecureDocSystem/samples"
    results_dir:  str = "/home/fun/SecureDocSystem/results"

    # ── Files to transfer to Pi (relative to local project root) ─────────────
    # Private key is intentionally excluded.
    sample_files: list = field(default_factory=lambda: [
        "samples/watermarked.png",
        "samples/watermarked2.png",
        "samples/manifest.json",
        "samples/manifest2.json",
        "samples/registry.json",
        "samples/registry2.json",
        "samples/provenance.json",
        "samples/provenance2.json",
    ])

    # ── SSH options ───────────────────────────────────────────────────────────
    # StrictHostKeyChecking=accept-new: auto-accept the Pi's host key on first
    # connect without prompting, but still record it for subsequent checks.
    ssh_opts: str = "-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.host}"

    @property
    def ssh_base(self) -> list[str]:
        """Base ssh command list for subprocess calls."""
        return ["ssh", "-p", str(self.ssh_port)] + self.ssh_opts.split() + [self.ssh_target]

    @property
    def scp_base(self) -> list[str]:
        """Base scp command list for subprocess calls."""
        return ["scp", "-P", str(self.ssh_port)] + self.ssh_opts.split()

    def remote_cmd(self, cmd: str) -> str:
        """Return a single ssh command string for shell use."""
        opts = self.ssh_opts
        return f'ssh -p {self.ssh_port} {opts} {self.ssh_target} "{cmd}"'

    def scp_to_pi(self, local_path: str, remote_path: str) -> str:
        """Return an scp command string for shell use."""
        opts = self.ssh_opts
        return f'scp -P {self.ssh_port} {opts} "{local_path}" {self.ssh_target}:"{remote_path}"'

    def scp_dir_to_pi(self, local_dir: str, remote_dir: str) -> str:
        """Return a recursive scp command string for shell use."""
        opts = self.ssh_opts
        return f'scp -r -P {self.ssh_port} {opts} "{local_dir}" {self.ssh_target}:"{remote_dir}"'


# Singleton — import PI from anywhere
PI = PiConfig()


if __name__ == "__main__":
    print("Pi deployment configuration")
    print(f"  Host         : {PI.host}:{PI.ssh_port}")
    print(f"  VNC port     : {PI.vnc_port}")
    print(f"  SSH user     : {PI.ssh_user}")
    print(f"  Project dir  : {PI.project_dir}")
    print(f"  Venv Python  : {PI.venv_python}")
    print(f"  SSH target   : {PI.ssh_target}")
    print(f"\n  SSH example  : {PI.remote_cmd('hostname')}")
