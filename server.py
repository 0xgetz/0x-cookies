"""
0x Cookies Local / VPS control panel.

A dependency-light server (Python stdlib http.server) that:
  - serves the web dashboard (web/index.html)
  - exposes a REST API to upload inputs, configs, proxies; start/pause/stop jobs
  - streams live stats over WebSocket (uses the `websockets` package if present,
    otherwise falls back to HTTP polling at /api/stats)

Run:
    python server.py --host 0.0.0.0 --port 8080
Open http://localhost:8080  (or http://<vps-ip>:8080)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core.config import Config
from core.engine import Job
from core.proxies import load_proxies

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# Auto-add bundled/extracted Chromium libs if present, so headless browser jobs
# work on a bare VPS without extra configuration.
def _bootstrap_libpath():
    extra = []
    for d in (ROOT / "third_party" / "lib",
              ROOT / "third_party" / "lib" / "x86_64-linux-gnu",
              ROOT / "third_party" / "lib" / "aarch64-linux-gnu"):
        if d.is_dir():
            extra.append(str(d))
    if extra:
        os.environ["LD_LIBRARY_PATH"] = ":".join(extra + [os.environ.get("LD_LIBRARY_PATH", "")]).rstrip(":")

_bootstrap_libpath()

STATE = {
    "job": None,
    "stats": {"total": 0, "tested": 0, "valid": 0, "invalid": 0, "errors": 0,
              "retries": 0, "banned": 0, "cpm": 0, "progress": 0,
              "running": False, "stopped": False, "paused": False, "elapsed": 0},
    "log": [],
    "inputs": [],
    "config": None,
    "proxies": [],
    "thread": None,
    "stop_flag": False,
}
LOCK = threading.Lock()
TOKEN = os.environ.get("OXC_TOKEN", "")


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    with LOCK:
        STATE["log"].append(f"[{ts}] {msg}")
        STATE["log"] = STATE["log"][-200:]


def run_job(config: Config, lines: list[str], opts: dict, proxies: list[str]):
    hits = DATA / "hits.txt"
    allr = DATA / "all.txt"
    hits.write_text("")
    allr.write_text("")
    from core.proxies import ProxyPool
    from core.proxies import parse_proxy_line

    plist = [p for p in (parse_proxy_line(x) for x in proxies) if p]
    pool = ProxyPool(plist, ban_seconds=opts.get("ban_seconds", 60),
                     max_fails=opts.get("max_fails", 3))
    job = Job(
        config=config, lines=lines, workers=opts.get("workers", 4),
        timeout=opts.get("timeout", 30), headless=opts.get("headless", True),
        pool=pool, hits_path=hits, all_path=allr,
        retry_on_fail=opts.get("retry", 0),
    )
    with LOCK:
        STATE["job"] = job
        STATE["stats"] = job.stats.as_dict()

    def _progress():
        # keep pushing live stats until the job sets finished_at
        while True:
            with LOCK:
                j = STATE["job"]
                if j is not None:
                    STATE["stats"] = j.stats.as_dict()
                    done = (j.stats.finished_at > 0)
                else:
                    done = True
            if done:
                return
            time.sleep(0.4)

    t = threading.Thread(target=_progress, daemon=True)
    t.start()
    log(f"job started: {config.name} — {len(lines)} lines, {opts.get('workers',4)} workers, "
        f"{len(plist)} proxies")
    try:
        asyncio.run(job.run())
    except Exception as e:
        log(f"job error: {type(e).__name__}: {str(e)[:160]}")
    finally:
        with LOCK:
            STATE["stats"] = job.stats.as_dict()
    log(f"job finished: valid={job.stats.valid} invalid={job.stats.invalid} "
        f"errors={job.stats.errors} cpm={job.stats.cpm:.1f}")


class Handler(BaseHTTPRequestHandler):
    server_version = "0xCookies/1.0"

    def log_message(self, *a):  # quieter
        pass

    # ---------- helpers ----------
    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n else b""

    def _read_json(self) -> dict:
        raw = self._read_body()
        try:
            return json.loads(raw or b"{}")
        except Exception:
            return {}

    def _authed(self) -> bool:
        if not TOKEN:
            return True
        return self.headers.get("X-Auth-Token", "") == TOKEN

    # ---------- routes ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            f = WEB / "index.html"
            if f.exists():
                return self._send(200, f.read_bytes(), "text/html; charset=utf-8")
            return self._send(404, b"index missing", "text/plain")
        if path == "/api/stats":
            with LOCK:
                return self._json({"stats": STATE["stats"], "log": STATE["log"]})
        if path == "/api/hits":
            f = DATA / "hits.txt"
            return self._send(200, f.read_bytes() if f.exists() else b"", "text/plain")
        if path == "/api/all":
            f = DATA / "all.txt"
            return self._send(200, f.read_bytes() if f.exists() else b"", "text/plain")
        if path == "/api/proxies":
            with LOCK:
                return self._json({"proxies": STATE["proxies"]})
        if path == "/api/inputs":
            with LOCK:
                return self._json({"count": len(STATE["inputs"])})
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/login" and not self._authed():
            return self._json({"error": "unauthorized"}, 401)

        if path == "/api/inputs":
            data = self._read_json()
            lines = data.get("lines") or []
            text = data.get("text", "")
            if text:
                lines = [l for l in text.splitlines()]
            lines = [l.strip() for l in lines if l.strip()]
            # dedupe preserving order
            seen = set(); dedup = []
            for l in lines:
                if l not in seen:
                    seen.add(l); dedup.append(l)
            with LOCK:
                STATE["inputs"] = dedup
            log(f"loaded {len(dedup)} inputs ({len(lines)-len(dedup)} dups removed)")
            return self._json({"count": len(dedup)})

        if path == "/api/config":
            data = self._read_json()
            if data.get("raw"):
                try:
                    cfg = Config.from_dict(json.loads(data["raw"]))
                except Exception as e:
                    return self._json({"error": f"bad config JSON: {e}"}, 400)
            else:
                cfg = Config.from_dict(data)
            errs = cfg.validate()
            if errs:
                return self._json({"error": errs}, 400)
            with LOCK:
                STATE["config"] = (json.loads(data["raw"]) if data.get("raw") else data)
            log(f"config loaded: {cfg.name} ({cfg.type})")
            return self._json({"ok": True, "name": cfg.name, "type": cfg.type})

        if path == "/api/proxies":
            data = self._read_json()
            text = data.get("text", "")
            good, bad = load_proxies(text)
            with LOCK:
                STATE["proxies"] = [p.url for p in good]
            log(f"loaded {len(good)} proxies ({len(bad)} invalid)")
            return self._json({"valid": len(good), "invalid": len(bad),
                               "proxies": [p.url for p in good][:50]})

        if path == "/api/start":
            with LOCK:
                if STATE["job"] is not None and STATE["stats"].get("running"):
                    return self._json({"error": "job already running"}, 409)
                if not STATE["config"]:
                    return self._json({"error": "no config loaded"}, 400)
                if not STATE["inputs"]:
                    return self._json({"error": "no inputs loaded"}, 400)
                cfg = Config.from_dict(STATE["config"])
                lines = list(STATE["inputs"])
                proxies = list(STATE["proxies"])
            opts = self._read_json() or {}
            STATE["stop_flag"] = False
            t = threading.Thread(target=run_job, args=(cfg, lines, opts, proxies), daemon=True)
            STATE["thread"] = t
            t.start()
            return self._json({"ok": True})

        if path == "/api/stop":
            with LOCK:
                if STATE["job"] is not None:
                    STATE["job"].stop()
                    STATE["stop_flag"] = True
            log("stop requested")
            return self._json({"ok": True})

        if path == "/api/pause":
            with LOCK:
                if STATE["job"] is not None:
                    STATE["job"].pause()
                    STATE["stats"]["paused"] = True
            return self._json({"ok": True})

        if path == "/api/resume":
            with LOCK:
                if STATE["job"] is not None:
                    STATE["job"].resume()
                    STATE["stats"]["paused"] = False
            return self._json({"ok": True})

        if path == "/api/clear":
            with LOCK:
                STATE["inputs"] = []
                STATE["log"] = []
                STATE["stats"] = {k: (0 if isinstance(v, int) or isinstance(v, float) else False)
                                  for k, v in STATE["stats"].items()}
            return self._json({"ok": True})

        return self._json({"error": "not found"}, 404)


def main():
    ap = argparse.ArgumentParser(description="0x Cookies control panel")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-ws", action="store_true", help="disable the WebSocket live feed")
    args = ap.parse_args()

    if not args.no_ws:
        try:
            _start_ws(args.host, args.port + 1)
        except Exception as e:
            print(f"[0x Cookies] WebSocket disabled ({e}); UI will poll /api/stats")

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[0x Cookies] panel running at http://{args.host}:{args.port}  (Ctrl+C to stop)")
    if TOKEN:
        print("[0x Cookies] API token required via X-Auth-Token header")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[0x Cookies] shutting down")


def _start_ws(host: str, ws_port: int):
    """Run a WebSocket server in a background thread that pushes live stats."""
    import websockets

    clients: set = set()

    async def handler(ws):
        clients.add(ws)
        try:
            async for _ in ws:
                pass
        except Exception:
            pass
        finally:
            clients.discard(ws)

    async def pump():
        while True:
            await asyncio.sleep(0.5)
            with LOCK:
                payload = json.dumps({"stats": STATE["stats"], "log": STATE["log"]})
            if clients:
                await asyncio.gather(*(c.send(payload) for c in list(clients)),
                                     return_exceptions=True)

    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from websockets.asyncio.server import serve as ws_serve
        async def go():
            async with ws_serve(handler, host, ws_port, origins=None):
                await pump()
        loop.run_until_complete(go())

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    # patch the dashboard to use the ws port (served via a tiny inline rewrite)
    Handler.WS_PORT = ws_port
    print(f"[0x Cookies] live WebSocket on ws://{host}:{ws_port}")


if __name__ == "__main__":
    main()
