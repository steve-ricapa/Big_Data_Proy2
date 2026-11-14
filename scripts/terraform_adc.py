"""Bridge Python-compatible impersonated ADC to Terraform via a runtime token.

Never prints/persists token, passes it only in the child process environment.
No credential files are opened directly, no ADC configuration is changed.
"""

import os
import subprocess
import sys
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request

credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
credentials.refresh(Request())
environment = dict(os.environ)
environment["GOOGLE_OAUTH_ACCESS_TOKEN"] = credentials.token
environment.pop("TF_LOG", None)  # Provider debug logging must never expose auth headers.
environment.pop("TF_LOG_PATH", None)
executable = Path.home() / "AppData/Local/Temp/opencode/terraform/terraform.exe"
if not executable.exists():
    executable = Path("terraform")
root = Path(__file__).resolve().parents[1]
result = subprocess.run([str(executable), "-chdir=infrastructure/terraform/environments/dev", *sys.argv[1:]], cwd=root, env=environment, check=False)
raise SystemExit(result.returncode)
