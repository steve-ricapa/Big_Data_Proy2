"""Execute a script inside the cloud airflow3-scheduler container."""

import os
import subprocess
import sys

os.chdir("/opt/threat-intelligence")
compose = ["bash", "scripts/cloud_compose.sh"]
subprocess.run([*compose, "exec", "-T", "airflow3-scheduler", "python", "/opt/project/scripts/" + sys.argv[1], *sys.argv[2:]], check=True)
