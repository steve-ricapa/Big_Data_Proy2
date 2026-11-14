"""Convenience wrapper for the approved remote Compose overlays over IAP."""

import shlex
import subprocess
import sys

root = "/opt/threat-intelligence"
command = ["sudo", "docker", "compose", "--project-directory", root, "--env-file", root + "/secrets/public.env"]
for name in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
    command += ["-f", root + "/" + name]
command += sys.argv[1:]
result = subprocess.run([sys.executable, "scripts/gcp_remote.py", "--command", shlex.join(command)], check=False)
raise SystemExit(result.returncode)
