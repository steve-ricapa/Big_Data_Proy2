"""Convenience wrapper for the approved remote Compose overlays over IAP."""

import shlex
import subprocess
import sys

command = ["sudo", "bash", "/opt/threat-intelligence/scripts/cloud_compose.sh", *sys.argv[1:]]
result = subprocess.run([sys.executable, "scripts/gcp_remote.py", "--command", shlex.join(command)], check=False)
raise SystemExit(result.returncode)
