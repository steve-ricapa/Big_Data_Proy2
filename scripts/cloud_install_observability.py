"""Install only this project's timer/unit and run one actual telemetry sample."""

import shutil
import subprocess
from pathlib import Path

source = Path.cwd()
root = Path("/opt/threat-intelligence")
shutil.copyfile(source / "cloud_observe.py", root / "scripts/cloud_observe.py")
for name in ("ti-health.service", "ti-health.timer"):
    shutil.copyfile(source / name, Path("/etc/systemd/system") / name)
subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["python3", str(root / "scripts/cloud_observe.py")], check=True)
subprocess.run(["systemctl", "enable", "--now", "ti-health.timer"], check=True)
print("Bounded health telemetry installed and first sample posted; no raw container logs exported.")
