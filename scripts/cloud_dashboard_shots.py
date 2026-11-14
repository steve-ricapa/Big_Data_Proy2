"""Capture the five cloud dashboard views with real Chrome via CDP.

Basic Auth is injected with Network.setExtraHTTPHeaders from VM credentials
loaded over IAP: never printed, logged, or embedded in command lines.
Run only when no DAG load is in progress.
"""

import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

from cloud_test_credentials import load

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ti-136-114-21-18.sslip.io"
VIEWS = ["Overview", "Vulnerability Explorer", "Threat Analytics", "Graph Intelligence", "Data Pipeline"]
OUT = ROOT / "docs/evidence/screenshots"
PORT = 9223


def chrome_process():
    profile = tempfile.mkdtemp(prefix="ti-shots-")
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
    password = load()["web-password"]
    token = base64.b64encode(f"ti-demo:{password}".encode()).decode()
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
        await send("Network.enable")
        await send("Network.setExtraHTTPHeaders", {"headers": {"Authorization": "Basic " + token}})
        await send("Page.navigate", {"url": BASE + "/"})
        for _ in range(90):
            title = await evaluate("document.title")
            metrics = await evaluate("document.querySelectorAll('[data-testid=stMetric]').length")
            if title and "Threat Intelligence" in title and metrics and int(metrics) > 0:
                break
            time.sleep(1)
        else:
            raise TimeoutError("Dashboard did not render")
        labels = await evaluate("[...document.querySelectorAll('[data-testid=stSidebar] [role=radiogroup] label')].map(l=>l.textContent)")
        assert labels == VIEWS, f"Unexpected views: {labels}"
        result = {"url": BASE, "views": []}
        for index, view in enumerate(VIEWS):
            if index > 0:
                await evaluate(f"document.querySelectorAll('[data-testid=stSidebar] [role=radiogroup] label')[{index}].click()")
            for _ in range(60):
                skeleton = await evaluate("document.querySelectorAll('[data-testid=stSkeleton]').length")
                if skeleton is not None and int(skeleton) == 0:
                    time.sleep(1)
                    break
                time.sleep(1)
            time.sleep(8)
            if view == "Graph Intelligence":
                clicked = await evaluate("(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Explorar relaciones'));if(!b)return false;b.click();return true})()")
                assert clicked, "Graph exploration button missing"
                for _ in range(60):
                    if await evaluate("document.body.innerText.includes('Subgrafo limitado')"):
                        break
                    time.sleep(1)
                else:
                    raise TimeoutError("Graph relationships did not render")
            assert not await evaluate("document.querySelector('[data-testid=stException]') !== null"), f"Exception in {view}"
            shot = await send("Page.captureScreenshot", {"format": "png"})
            path = OUT / f"gcp_dashboard_{view.lower().replace(' ', '_')}.png"
            path.write_bytes(base64.b64decode(shot["data"]))
            result["views"].append({"view": view, "file": str(path.relative_to(ROOT)), "bytes": path.stat().st_size})
        await ws.close()
        (ROOT / "docs/evidence/gcp_dashboard_browser_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        chrome.terminate()
        chrome.wait(timeout=15)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
