"""Read official Compute Engine SKU catalog through ADC; no token output."""

import json
from datetime import UTC, datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
selected = []
with AuthorizedSession(credentials) as session:
    page = None
    pages = 0
    while True:
        params = {"currencyCode": "USD", "pageSize": 5000}
        if page:
            params["pageToken"] = page
        response = session.get("https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus", params=params, headers={"x-goog-user-project": "proyectobigdata2-514216"}, timeout=90)
        response.raise_for_status()
        data = response.json()
        pages += 1
        for sku in data.get("skus", []):
            description = sku["description"]
            match = ("E2 Instance" in description and ("Core" in description or "Ram" in description or "RAM" in description)) or "Balanced PD Capacity" in description or "External IP Charge" in description
            if match and "us-central1" in sku.get("serviceRegions", []) and sku.get("category", {}).get("usageType") == "OnDemand":
                selected.append(sku)
        page = data.get("nextPageToken")
        if not page:
            break
result = {"checked_at": datetime.now(UTC).isoformat(), "source": "Google Cloud Billing Catalog API", "region": "us-central1", "currency": "USD", "pages_read": pages, "skus": selected}
Path("docs/evidence/gcp_official_skus.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
for sku in selected:
    expression = sku["pricingInfo"][-1]["pricingExpression"]
    print(json.dumps({"description": sku["description"], "sku": sku["skuId"], "unit": expression["usageUnit"], "tiers": expression["tieredRates"]}))
