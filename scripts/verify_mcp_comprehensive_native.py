"""Run the same semantic suite through installed Codex native OAuth transport.

Never starts a login or reads credentials. If the stored session expired, stop
with PENDING_USER_LOGIN. This is a separate process, not GUI confirmation.
"""
import argparse
import asyncio
import json
import os
import queue
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import verify_mcp_comprehensive as suite
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, Tool

ROOT = Path(__file__).resolve().parents[1]
NAME = "big_data_ii_-_threat_intelligence"


class NativeRPC:
    def __init__(self, binary):
        self.process = subprocess.Popen(
            [str(binary), "-c", "mcp_servers.node_repl.enabled=false", "app-server", "--stdio"],
            cwd=ROOT, env=dict(os.environ, CODEX_HOME=str(Path.home() / ".codex")),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        self.messages = queue.Queue()
        self.counter = 0
        threading.Thread(target=self.consume, daemon=True).start()
        threading.Thread(target=self.discard_stderr, daemon=True).start()

    def consume(self):
        for line in self.process.stdout:
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                pass

    def discard_stderr(self):
        for _line in self.process.stderr:
            pass  # No raw authorization/transport diagnostics enter evidence.

    def request(self, method, params):
        self.counter += 1
        identity = self.counter
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": identity, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                response = self.messages.get(timeout=0.3)
            except queue.Empty:
                if self.process.poll() is not None:
                    raise RuntimeError("Native diagnostic process exited") from None
                continue
            if response.get("id") != identity:
                continue
            if "error" in response:
                raise RuntimeError("Native RPC rejected method; raw body suppressed")
            return response.get("result", {})
        raise TimeoutError("Native RPC timed out")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


class NativeTools:
    def __init__(self, rpc, thread, tools):
        self.rpc, self.thread, self.tools = rpc, thread, tools

    async def list_tools(self):
        return [Tool.model_validate({**value, "name": key}) for key, value in self.tools.items()]

    async def call_tool(self, name, arguments):
        response = await asyncio.to_thread(self.rpc.request, "mcpServer/tool/call", {"threadId": self.thread, "server": NAME, "tool": name, "arguments": arguments})
        result = CallToolResult.model_validate(response)
        if result.isError:
            # The server's argument/API errors are value-redacting. Keep just
            # labels required for semantic negative assertions, not raw bodies.
            text = " ".join(getattr(v, "text", "") for v in result.content)
            markers = [tag for tag in ("Invalid arguments", "extra_forbidden", "HTTP 404", "HTTP 409", "HTTP 422") if tag in text]
            raise ToolError(" ".join(markers) if markers else "Native tool error; details suppressed")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path.home() / "AppData/Local/OpenAI/Codex/bin/9e1da79431da526b/codex.exe")
    args = parser.parse_args()
    out = {"at": datetime.now(UTC).isoformat(), "status": "PENDING_USER_LOGIN", "app_gui_confirmation": "PENDING", "credentials_changed": False}
    rpc = NativeRPC(args.binary)
    try:
        rpc.request("initialize", {"clientInfo": {"name": "ti-comprehensive-native-verifier", "version": "1.0"}, "capabilities": {"experimentalApi": True}})
        rpc.process.stdin.write('{"jsonrpc":"2.0","method":"initialized"}\n')
        rpc.process.stdin.flush()
        inventory = rpc.request("mcpServerStatus/list", {"detail": "full", "limit": 100})
        target = next((s for s in inventory["data"] if s["name"] == NAME), None)
        out["authStatus"] = target.get("authStatus") if target else "missing_server"
        if not target or target.get("authStatus") != "oAuth":
            return out
        thread = rpc.request("thread/start", {"cwd": str(ROOT), "ephemeral": True, "sandbox": "read-only", "approvalPolicy": "on-request"})["thread"]["id"]
        inventory = rpc.request("mcpServerStatus/list", {"detail": "full", "limit": 100, "threadId": thread})
        target = next(s for s in inventory["data"] if s["name"] == NAME)
        if len(target.get("tools", {})) != 6:
            out["status"] = "FAIL_NATIVE_DISCOVERY"
            return out
        suite.server.mcp = NativeTools(rpc, thread, target["tools"])
        os.environ["NVD_FIXTURE"] = str(ROOT / "docs/evidence/codex_functional/nvd_CVE-2021-44228.json")
        out["semantic_suite"] = asyncio.run(suite.run())
        out["semantic_suite"]["transport"] = "Installed Codex native app-server -> authenticated public MCP -> FastAPI -> databases"
        out["semantic_suite"]["oauth_e2e"] = "EXECUTED_NATIVE_NOT_GUI"
        if out["semantic_suite"]["status"] == "BASELINE_REFRESH_REQUIRED":
            out["status"] = "BASELINE_REFRESH_REQUIRED"
        else:
            out["status"] = "PASS_NATIVE_OAUTH_SUITE" if out["semantic_suite"]["status"] == "PASS_INTEGRATION_NOT_OAUTH_E2E" else "FAIL_NATIVE_SEMANTICS"
    except (RuntimeError, TimeoutError, OSError, KeyError) as error:
        out["status"] = "FAIL_NATIVE_PROBE"
        out["exception_type"] = type(error).__name__
    finally:
        rpc.close()
        (ROOT / "docs/evidence/codex_diagnosis/comprehensive_native_suite.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    result = main()
    print(json.dumps({k: v for k, v in result.items() if k != "semantic_suite"}, indent=2))
    raise SystemExit(0 if result["status"] == "PASS_NATIVE_OAUTH_SUITE" else 1)
