"""Verify the Airflow 3.4 UI through the IAP SSH tunnel with real Chrome.

Requires an active tunnel: gcloud compute ssh ti-dev-data --tunnel-through-iap
--ssh-flag="-L 18081:localhost:18081". Login credentials are read from the
local secret file and injected into the form; never printed or logged.
"""

import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:18081"
OUT = ROOT / "docs/evidence/screenshots"
PORT = 9224


def load_admin_password():
    """Fetch the Airflow SimpleAuthManager passwords file from the VM over IAP.

    The password lives only in process memory; never printed or logged.
    """
    import shlex

    code = "import json;from pathlib import Path;print(json.load(open('/opt/threat-intelligence/secrets/airflow3-passwords'))['admin'])"
    command = "sudo python3 -c " + shlex.quote(code)
    result = subprocess.run([sys.executable, "scripts/gcp_remote.py", "--command", command], check=True, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip().splitlines()[-1]


def chrome_process():
    profile = tempfile.mkdtemp(prefix="ti-airflow-")
    args = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={profile}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1680,1050",
        "--hide-scrollbars",
        "about:blank",
    ]
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_ready():
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.5)
    raise TimeoutError("Chrome did not start")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    password = load_admin_password()
    chrome = chrome_process()
    try:
        wait_ready()
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=5) as response:
            targets = [t for t in json.load(response) if t["type"] == "page"]
        ws = await websockets.connect(targets[0]["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024)
        counter = 0

        async def send(method, params=None):
            nonlocal counter
            counter += 1
            await ws.send(json.dumps({"id": counter, "method": method, "params": params or {}}))
            while True:
                message = json.loads(await ws.recv())
                if message.get("id") == counter:
                    if "error" in message:
                        raise RuntimeError(f"{method}: {message['error']}")
                    return message.get("result", {})

        async def evaluate(expression):
            result = await send("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
            return result.get("result", {}).get("value")

        await send("Page.enable")
        await send("Page.navigate", {"url": BASE + "/home"})
        time.sleep(6)
        logged_in = "nvd_threat_intelligence" in (await evaluate("document.body.innerText") or "")
        login = "no-form"
        if not logged_in:
            login = await evaluate(
                "(function(){const u=document.querySelector('input[name=username]')||document.querySelector('input[type=text]');const p=document.querySelector('input[name=password]')||document.querySelector('input[type=password]');if(!u||!p)return 'no-form';u.value='admin';p.value="
                + json.dumps(password)
                + ";const b=document.querySelector('button[type=submit]')||document.querySelector('button');if(b)b.click();return 'submitted'})()"
            )
            for _ in range(30):
                time.sleep(2)
                if "nvd_threat_intelligence" in (await evaluate("document.body.innerText") or ""):
                    logged_in = True
                    break
        await send("Page.navigate", {"url": BASE + "/dags/nvd_threat_intelligence/grid"})
        time.sleep(10)
        body = (await evaluate("document.body.innerText") or "")[:2000]
        shot = await send("Page.captureScreenshot", {"format": "png"})
        path = OUT / "gcp_airflow_ui_grid.png"
        path.write_bytes(base64.b64decode(shot["data"]))
        await ws.close()
        print(json.dumps({"login": login, "logged_in": logged_in, "grid_shows_dag": "nvd_threat_intelligence" in body, "file": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "body_sample": body[:300]}, indent=2))
    finally:
        chrome.terminate()
        chrome.wait(timeout=15)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
