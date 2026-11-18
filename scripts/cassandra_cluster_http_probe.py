"""Assert Cassandra-backed readiness and snapshot through the live local API."""

import json
from urllib.request import urlopen


def get(path):
    with urlopen("http://127.0.0.1:18000" + path, timeout=30) as response:
        return json.load(response)


ready = get("/ready")
assert ready["status"] == "ready" and "cassandra" in ready["checked"]
result = get("/api/v1/analytics/cassandra/snapshot")
assert result["source"] == "cassandra" and result["snapshot"]["total_cves"] >= 50000
print(json.dumps({"ready": ready, "source": result["source"], "as_of": result["snapshot"]["as_of"], "total_cves": result["snapshot"]["total_cves"]}))
