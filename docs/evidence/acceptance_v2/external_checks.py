"""Reuse audit probes, writing a separate v2 evidence set."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
probe = root / "docs/evidence/acceptance/external_checks.py"
source = probe.read_text(encoding="utf-8").replace("docs/evidence/acceptance/", "docs/evidence/acceptance_v2/")
exec(compile(source, str(probe), "exec"), {"__name__": "__main__", "__file__": str(probe)})
