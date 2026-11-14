"""Run isolated cloud unit tests, never mount production data or networking."""
import subprocess
from pathlib import Path

root = Path('/opt/threat-intelligence')
args = ['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', '--memory', '512m', '--read-only', '--tmpfs', '/tmp', '-e', 'TI_INTEGRATION=0', '-e', 'TI_SECURE_TESTS=0', '--mount', f'type=bind,source={root / "tests"},target=/app/tests,readonly', '--entrypoint', 'python', 'ti-test:local', '-m', 'pytest', '/app/tests', '-q', '-p', 'no:cacheprovider', '--basetemp=/tmp/pytest']
raise SystemExit(subprocess.run(args).returncode)
