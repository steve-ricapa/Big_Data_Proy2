"""Private test credential transfer over IAP, only inside the test process memory.

Do not call this module as a command or print its return value. No secrets in
argv, logs, tool output, report files or Terraform state.
"""

import json
import subprocess
import sys


def load():
    names = ["web-password", "keycloak-user-password", "mcp-oauth-client-secret"]
    code = "import json;from pathlib import Path;print(json.dumps({n:(Path('/opt/threat-intelligence/secrets')/n).read_text().strip() for n in " + repr(names) + "}))"
    import shlex

    command = "sudo python3 -c " + shlex.quote(code)
    result = subprocess.run([sys.executable, "scripts/gcp_remote.py", "--command", command], check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Private IAP credential transfer failed; output suppressed")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise RuntimeError("Unexpected IAP credential transfer response; output suppressed") from None
