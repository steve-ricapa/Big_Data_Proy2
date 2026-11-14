"""Non-destructive local syntax/config/lock validation, no deployment."""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = {}
    bash = next((str(p) for p in (Path("C:/Program Files/Git/bin/bash.exe"), Path("C:/Program Files/Git/usr/bin/bash.exe")) if p.exists()), "bash")
    for path in (ROOT / "scripts").glob("*.sh"):
        p = subprocess.run([bash, "-n", path.as_posix()], capture_output=True)
        checks[path.relative_to(ROOT).as_posix()] = "PASS" if p.returncode == 0 else "FAIL"
    environment = dict(os.environ, TI_PUBLIC_URL="https://ti-136-114-21-18.sslip.io", TI_HOSTNAME="ti-136-114-21-18.sslip.io")
    args = ["docker", "compose"]
    for name in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
        args += ["-f", name]
    p = subprocess.run([*args, "config", "--quiet"], cwd=ROOT, env=environment, capture_output=True)
    checks["compose_config_local_no_daemon"] = "PASS" if p.returncode == 0 else "FAIL"
    p = subprocess.run(["uv", "lock", "--check"], cwd=ROOT, capture_output=True)
    checks["uv_lock_check"] = "PASS" if p.returncode == 0 else "FAIL"
    # Parse PowerShell scripts without executing startup/shutdown/deployment.
    command = "$ErrorActionPreference='Stop'; $bad=0; Get-ChildItem scripts -Filter *.ps1 | ForEach-Object { $tokens=$null; $errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors); if($errors.Count -gt 0){$bad++} }; exit $bad"
    p = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], cwd=ROOT, capture_output=True)
    checks["powershell_parse_only"] = "PASS" if p.returncode == 0 else "FAIL"
    result = {"at": datetime.now(UTC).isoformat(), "checks": checks, "status": "PASS" if all(v == "PASS" for v in checks.values()) else "PARTIAL"}
    (ROOT / "docs/evidence/acceptance_v2/input_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
