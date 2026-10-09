"""
Job engine: OpenBullet-style check runner.

Runs a Config against a list of input lines using N concurrent workers.
Supports:
  - http checks (urllib, with proxy) and browser checks (Playwright Chromium)
  - proxy pool rotation + ban/retry
  - retries on error/ban
  - live stats (tested/hits/fails/retries/errors, CPM, progress)
  - captures extraction
  - hits written to file as they are found
"""
from __future__ import annotations

import asyncio
import base64
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config, parse_input_line, render
from .proxies import Proxy, ProxyPool


def _make_proxy_handler(p: Proxy | None):
    if p is None:
        return None
    scheme = "socks5" if p.scheme.startswith("socks5") else p.scheme
    auth = ""
    if p.user:
        raw = f"{p.user}:{p.passwd}".encode()
        auth = base64.b64encode(raw).decode()
    # urllib only natively supports http/https proxies; socks needs PySocks.
    if scheme.startswith("socks"):
        try:
            import socks  # type: ignore
            return None  # handled by opening a socks socket below
        except Exception:
            return None
    url = f"{p.scheme}://{p.host}:{p.port}"
    handler = urllib.request.ProxyHandler({"http": url, "https": url})
    return handler


@dataclass
class JobStats:
    total: int = 0
    tested: int = 0
    valid: int = 0
    invalid: int = 0
    errors: int = 0
    retries: int = 0
    banned: int = 0
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    running: bool = False
    stopped: bool = False
    paused: bool = False

    @property
    def cpm(self) -> float:
        elapsed = (self.finished_at or time.time()) - self.started_at
        return (self.tested / elapsed * 60.0) if elapsed > 0 else 0.0

    @property
    def progress(self) -> float:
        return (self.tested / self.total * 100.0) if self.total else 0.0

    def as_dict(self) -> dict:
        return {
            "total": self.total, "tested": self.tested,
            "valid": self.valid, "invalid": self.invalid,
            "errors": self.errors, "retries": self.retries,
            "banned": self.banned, "cpm": round(self.cpm, 2),
            "progress": round(self.progress, 2),
            "running": self.running, "stopped": self.stopped, "paused": self.paused,
            "elapsed": round((self.finished_at or time.time()) - self.started_at, 1),
        }


@dataclass
class Job:
    config: Config
    lines: list[str]
    workers: int = 4
    timeout: int = 30
    headless: bool = True
    pool: ProxyPool = field(default_factory=ProxyPool)
    hits_path: Path | None = None
    all_path: Path | None = None
    retry_on_fail: int = 0

    stats: JobStats = field(default_factory=JobStats)
    _results: list[dict] = field(default_factory=list)
    _lock: asyncio.Lock | None = None
    _pause_event: asyncio.Event | None = None
    _stop: bool = False
    _browser = None

    # ---- result sink ----
    def _append_result(self, r: dict):
        self._results.append(r)
        if self.all_path:
            with open(self.all_path, "a", encoding="utf-8") as fh:
                fh.write(f"{r['status']}\t{r['line']}\t{r.get('detail','')}\n")
        if r["status"] == "valid" and self.hits_path:
            with open(self.hits_path, "a", encoding="utf-8") as fh:
                cap = r.get("captures", {})
                capstr = " | ".join(f"{k}={v}" for k, v in cap.items())
                fh.write(f"{r['line']}" + (f"\t{capstr}" if capstr else "") + "\n")

    def results(self) -> list[dict]:
        return list(self._results)

    # ---- checks ----
    async def _check_http(self, line: str, proxy: Proxy | None) -> dict:
        vars_ = parse_input_line(line, self.config.input_format)
        url = render(self.config.url, vars_)
        headers = {k: render(v, vars_) for k, v in self.config.headers.items()}
        data = render(self.config.body, vars_).encode() if self.config.body else None
        if data and "Content-Type" not in headers:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        def _do():
            handlers = []
            ph = _make_proxy_handler(proxy)
            if ph:
                handlers.append(ph)
            if proxy and proxy.scheme.startswith("socks"):
                import socks  # type: ignore
                import socket
                sock = socks.socksocket()
                sock.set_proxy(getattr(socks, "SOCKS5" if "5" in proxy.scheme else "SOCKS4"),
                               proxy.host, proxy.port,
                               username=proxy.user or None, password=proxy.passwd or None)
                sock.settimeout(self.timeout)
                # manual HTTP over socks via urllib is complex; do a raw request
                return _raw_http(url, self.config.method, headers, data, sock, self.timeout)
            opener = urllib.request.build_opener(*handlers)
            req = urllib.request.Request(url, data=data, headers=headers,
                                         method=self.config.method)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with opener.open(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
                return resp.geturl(), resp.status, body

        final_url, status, body = await asyncio.get_event_loop().run_in_executor(None, _do)
        return {"final_url": final_url, "status": status, "body": body}

    async def _check_browser(self, line: str, proxy: Proxy | None) -> dict:
        from playwright.async_api import async_playwright  # noqa
        vars_ = parse_input_line(line, self.config.input_format)
        url = render(self.config.url, vars_)
        ctx_kwargs = {"user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")}
        if proxy is not None:
            ctx_kwargs["proxy"] = proxy.to_playwright()
        context = await self._browser.new_context(**ctx_kwargs)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            try:
                await page.wait_for_timeout(1500)
            except Exception:
                pass
            body = await page.content()
            final_url = page.url
            status = None
            return {"final_url": final_url, "status": status, "body": body}
        finally:
            await page.close()
            await context.close()

    async def _handle(self, line: str):
        if self._lock is None:
            self._lock = asyncio.Lock()
        attempts = max(1, self.config.retry + self.retry_on_fail)
        last = None
        for attempt in range(attempts):
            if self._stop:
                return
            if self._pause_event is not None and self._pause_event.is_set():
                await self._pause_event.wait()
            proxy = self.pool.next() if self.pool.enabled else None
            try:
                if self.config.type == "browser":
                    res = await self._check_browser(line, proxy)
                else:
                    res = await self._check_http(line, proxy)
            except Exception as e:
                last = {"status": "error", "line": line, "detail": f"{type(e).__name__}: {str(e)[:120]}",
                        "captures": {}, "proxy": proxy.url if proxy else "", "final_url": ""}
                self.pool.report(proxy, False)
                async with self._lock:
                    self.stats.errors += 1
                    self.stats.retries += 1 if attempt < attempts - 1 else 0
                await asyncio.sleep(0.5)
                continue

            # success/fail evaluation
            vars_ = parse_input_line(line, self.config.input_format)
            final_url = res.get("final_url", "")
            body = res.get("body", "")
            status = res.get("status")
            caps = {}
            for c in self.config.captures:
                m = re.search(c.regex, body, re.I | re.S)
                if m:
                    try:
                        caps[c.name] = m.group(c.group)
                    except Exception:
                        caps[c.name] = m.group(0)

            ok = self.config.success.matches(final_url, body, status) or _matches_rendered(
                self.config.success, final_url, body, status, vars_)
            bad = self.config.fail.matches(final_url, body, status) or _matches_rendered(
                self.config.fail, final_url, body, status, vars_)
            # fail conditions take precedence: landing on a login/error page is a
            # hard "invalid" even if a loose success regex would also match.
            if bad:
                verdict = "invalid"
            elif ok:
                verdict = "valid"
            else:
                verdict = "invalid"

            out = {"status": verdict, "line": line,
                   "detail": f"{final_url[:70]}",
                   "captures": caps, "proxy": proxy.url if proxy else "",
                   "final_url": final_url}
            self.pool.report(proxy, verdict == "valid")
            async with self._lock:
                self.stats.tested += 1
                if verdict == "valid":
                    self.stats.valid += 1
                    self._append_result(out)
                else:
                    self.stats.invalid += 1
                if self.all_path and verdict != "valid":
                    self._append_result(out)
            return

        if last is not None:
            async with self._lock:
                self.stats.tested += 1
                self._append_result(last)

    async def run(self):
        self.stats = JobStats(total=len(self.lines))
        self.stats.running = True
        self._stop = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()

        need_browser = self.config.type == "browser"
        pw = None
        if need_browser:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled"],
            )
        sem = asyncio.Semaphore(self.workers)

        async def worker(line):
            async with sem:
                await self._handle(line)

        try:
            await asyncio.gather(*(worker(l) for l in self.lines))
        finally:
            if self._browser:
                await self._browser.close()
            if pw:
                await pw.stop()
            self.stats.running = False
            self.stats.finished_at = time.time()

    def stop(self):
        self._stop = True

    def pause(self):
        if self._pause_event is not None:
            self._pause_event.clear()

    def resume(self):
        if self._pause_event is not None:
            self._pause_event.set()


def _matches_rendered(rule, url: str, body: str, status, vars_: dict) -> bool:
    """Evaluate a Rule after substituting <USER>/<PASS>/… placeholders."""
    from .config import Rule
    r2 = Rule(render(rule.url_regex, vars_), render(rule.body_regex, vars_), rule.status)
    return r2.matches(url, body, status)


def _raw_http(url, method, headers, data, sock, timeout):
    """Minimal HTTP/1.1 over a socks socket."""
    import socket
    u = urllib.parse.urlparse(url)
    host = u.hostname
    port = u.port or (443 if u.scheme == "https" else 80)
    try:
        sock.connect((host, port))
    except Exception as e:
        raise e
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    hdrs = dict(headers)
    hdrs["Host"] = u.netloc
    hdrs["Connection"] = "close"
    body_b = data or b""
    hdrs["Content-Length"] = str(len(body_b))
    req = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in hdrs.items()) + "\r\n"
    sock.sendall(req.encode() + body_b)
    raw = b""
    sock.settimeout(timeout)
    while True:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        raw += chunk
        if len(raw) > 3_000_000:
            break
    sock.close()
    text = raw.decode("utf-8", "replace")
    head, _, body = text.partition("\r\n\r\n")
    status = 0
    first = head.splitlines()[0] if head else ""
    parts = first.split()
    if len(parts) >= 2 and parts[1].isdigit():
        status = int(parts[1])
    return url, status, body
