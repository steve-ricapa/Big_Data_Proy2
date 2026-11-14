"""Transfer only allowlisted closure artifacts; never read runtime secrets."""

import json
from pathlib import Path

root = Path("/opt/threat-intelligence/docs/evidence/acceptance_v2")
names = ("cloud_tests.log", "cloud_tests.xml", "crud.json", "component_health.json", "rebuild.json", "rebuild_initial.json", "restore_three.json", "restore_three_local.json", "restore_three_initial.json", "verification-image.json", "build_app.log", "build_test.log", "build_mcp.log", "build_airflow.log")
print(json.dumps({name: (root / name).read_text(encoding="utf-8") for name in names if (root / name).exists()}))
