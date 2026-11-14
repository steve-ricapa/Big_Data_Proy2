"""Run explicit project commands over IAP SSH; can stream a local script to stdin."""

import argparse
import hashlib
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--command", required=True)
parser.add_argument("--stdin-file")
args = parser.parse_args()
gcloud = "gcloud.cmd" if os.name == "nt" else "gcloud"
common = ["--project=proyectobigdata2-514216", "--zone=us-central1-a", "--tunnel-through-iap", "--quiet"]
remote_command = args.command
if args.stdin_file:
    # Windows gcloud/PuTTY prepends an automatic host-key confirmation to stdin.
    # SCP the source instead, so that 'y' cannot become executable Python input.
    data = Path(args.stdin_file).read_bytes()
    remote_name = "ti-script-" + hashlib.sha256(data).hexdigest()[:16] + ".py"
    subprocess.run([gcloud, "compute", "scp", args.stdin_file, "ti-dev-data:" + remote_name, *common], check=True, env=dict(os.environ))
    if "python3 -" not in remote_command:
        raise ValueError("stdin-file requires a python3 - command")
    remote_command = remote_command.replace("python3 -", "python3 " + remote_name, 1)
command = [gcloud, "compute", "ssh", "ti-dev-data", *common, "--command", remote_command]
result = subprocess.run(command, check=False, env=dict(os.environ))
raise SystemExit(result.returncode)
