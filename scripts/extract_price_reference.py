"""Extract only relevant VM pricing rows from an official locally fetched HTML."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

source = Path.home() / "AppData/Local/Temp/opencode/gcp-pricing.html"
html = source.read_text(encoding="utf-8")
rows = re.findall(r"<tr[^>]*>.*?</tr>", html, re.DOTALL)
selected = [
    re.sub(r"<[^>]+>", " ", row)
    for row in rows
    if "e2-standard-4" in row or "e2-standard-8" in row
]
evidence = {
    "url": "https://cloud.google.com/products/compute/pricing/general-purpose",
    "extracted_at": datetime.now(UTC).isoformat(),
    "rows": selected,
    "limitation": "Dynamic regional selector; reconfirm selected region/SKU before any deployment approval.",
}
Path("docs/evidence/gcp_price_reference.json").write_text(
    json.dumps(evidence, indent=2), encoding="utf-8"
)
print("Saved official pricing row references; not a billing quote.")
