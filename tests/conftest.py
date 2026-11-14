import pytest


@pytest.fixture
def cve():
    return {
        "id": "CVE-2024-12345",
        "published": "2024-01-02T10:00:00Z",
        "lastModified": "2026-11-01T12:00:00Z",
        "vulnStatus": "Analyzed",
        "descriptions": [{"lang": "en", "value": "Example"}],
        "metrics": {
            "cvssMetricV31": [
                {"type": "Primary", "cvssData": {"version": "3.1", "baseScore": 9.8}}
            ]
        },
        "weaknesses": [
            {"description": [{"value": "CWE-79"}, {"value": "NVD-CWE-noinfo"}]}
        ],
        "configurations": [
            {
                "nodes": [
                    {
                        "cpeMatch": [
                            {
                                "vulnerable": True,
                                "criteria": "cpe:2.3:a:vendor:product:1.0:*:*:*:*:*:*:*",
                            },
                            {
                                "vulnerable": False,
                                "criteria": "cpe:2.3:o:other:environment:*:*:*:*:*:*:*:*",
                            },
                        ]
                    }
                ]
            }
        ],
        "references": [{"url": "https://example.org/advisory"}],
    }
