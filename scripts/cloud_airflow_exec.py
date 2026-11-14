"""Execute a script inside the cloud airflow3-scheduler container."""

import os
import subprocess
import sys

os.chdir("/opt/threat-intelligence")
compose = ["docker", "compose", "--env-file", "secrets/public.env"]
for name in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
    compose += ["-f", name]
subprocess.run([*compose, "exec", "-T", "airflow3-scheduler", "python", "/opt/project/scripts/" + sys.argv[1], *sys.argv[2:]], check=True)
