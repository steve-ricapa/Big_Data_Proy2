import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (ROOT / "infrastructure/terraform").is_dir(),
    reason="Repository-input checks run in the checkout, not the minimal application test image",
)


def test_terraform_module_sources_and_bootstrap_exist():
    for path in (ROOT / "infrastructure/terraform").rglob("*.tf"):
        if ".terraform" in path.parts:
            continue
        for source in re.findall(r'source\s*=\s*"(\.[^"]+)"', path.read_text()):
            assert list((path.parent / source).glob("*.tf")), (path, source)
    assert (ROOT / "infrastructure/scripts/vm-bootstrap.sh").is_file()
    assert (ROOT / "infrastructure/terraform/environments/dev/.terraform.lock.hcl").is_file()


@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="Git ignore policy requires a checkout, not a Docker source copy")
def test_gitignore_preserves_code_but_rejects_private_material():
    candidates = [
        "secrets/web-password", "nested/secrets/key", "credentials/service.json", ".env", ".env.prod",
        "infrastructure/terraform/environments/dev/terraform.tfstate", "any.tfstate.backup", "any.tfplan",
        "tfplan.registry", "infrastructure/terraform/environments/dev/private.tfvars", "private.tfvars.json",
        "private.ppk", "private.p12", "private.pfx", "private.kdbx", ".terraformrc", "terraform.rc", ".codex/auth.json",
        "any.tfplan.bin",
        "infrastructure/terraform/modules/secrets/private.json", "infrastructure/terraform/modules/secrets/key.pem",
        "infrastructure/terraform/modules/secrets/main.tf", "infrastructure/terraform/modules/secrets/README.md",
    ]
    process = subprocess.run(
        ["git", "check-ignore", "--no-index", "-z", "--stdin"], input=("\0".join(candidates) + "\0").encode(),
        cwd=ROOT, capture_output=True, check=False,
    )
    assert process.returncode == 0
    assert set(process.stdout.decode().rstrip("\0").split("\0")) == set(candidates[:-2])


def test_secrets_module_declares_resources_not_secret_values():
    text = (ROOT / "infrastructure/terraform/modules/secrets/main.tf").read_text()
    assert 'resource "google_secret_manager_secret"' in text
    assert not re.search(r'resource\s+"google_secret_manager_secret_version"', text)
    assert not re.search(r"^\s*secret_data\s*=", text, flags=re.MULTILINE)
