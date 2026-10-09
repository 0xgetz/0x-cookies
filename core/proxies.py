"""
Proxy manager: load, parse, dedupe, rotate, ban/retry.

Supported input lines (one per line, '#' comments ignored):
    host:port
    user:pass@host:port
    scheme://host:port
    scheme://user:pass@host:port
where scheme in {http, https, socks4, socks5, socks5h}.

Thread/async-safe. Implements a simple "banned until N seconds after K fails"
policy so dead proxies are rotated out and retried later.
"""
from __future__ import annotations

import itertools
import re
import threading
import time
from dataclasses import dataclass, field


_SCHEMES = {"http", "https", "socks4", "socks5", "socks5h"}
_HOST_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
_LINE_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://")


@dataclass
class Proxy:
    scheme: str
    host: str
    port: int
    user: str = ""
    passwd: str = ""
    # runtime state
    uses: int = 0
    fails: int = 0
    ok: int = 0
    banned_until: float = 0.0
    checked: bool = False

    @property
    def auth(self) -> str:
        return f"{self.user}:{self.passwd}@" if self.user else ""

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.auth}{self.host}:{self.port}"

    @property
    def server(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

    def to_playwright(self) -> dict:
        d = {"server": self.server}
        if self.user:
            d["username"] = self.user
            d["password"] = self.passwd
        return d


def parse_proxy_line(line: str) -> Proxy | None:
    s = line.strip()
    if not s or s.startswith("#") or s.startswith("//"):
        return None
    scheme = ""
    m = _LINE_SCHEME_RE.match(s)
    if m:
        scheme = m.group(1).lower()
        s = s[m.end():]
    s = s.lstrip("/")

    user = passwd = ""
    at = s.rfind("@")
    hostport = s
    if at != -1:
        cred = s[:at]
        hostport = s[at + 1:]
        c = cred.split(":")
        user = c[0]
        passwd = ":".join(c[1:]) if len(c) > 1 else ""

    parts = hostport.split(":")
    if len(parts) == 2:
        host, port = parts
    elif len(parts) == 4:  # user:pass:host:port
        user = user or parts[0]
        passwd = passwd or parts[1]
        host, port = parts[2], parts[3]
    else:
        return None

    host = host.strip().strip("[]")
    if not host or not _HOST_RE.match(host):
        return None
    try:
        portn = int(port)
    except ValueError:
        return None
    if not (1 <= portn <= 65535):
        return None

    if scheme not in _SCHEMES:
        scheme = "http"
    return Proxy(scheme=scheme, host=host, port=portn, user=user, passwd=passwd)


def load_proxies(text: str) -> tuple[list[Proxy], list[str]]:
    """Return (proxies_deduped, invalid_lines)."""
    good: list[Proxy] = []
    bad: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#") or raw.strip().startswith("//"):
            continue
        p = parse_proxy_line(raw)
        if not p:
            bad.append(raw.strip()[:80])
            continue
        if p.url in seen:
            continue
        seen.add(p.url)
        good.append(p)
    return good, bad


class ProxyPool:
    """Async-safe rotating pool with ban policy."""

    def __init__(self, proxies: list[Proxy] | None = None,
                 ban_seconds: int = 60, max_fails: int = 3):
        self._proxies: list[Proxy] = proxies or []
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None
        self.ban_seconds = ban_seconds
        self.max_fails = max_fails
        self.enabled = bool(self._proxies)

    def __len__(self) -> int:
        return len(self._proxies)

    def set_proxies(self, proxies: list[Proxy]):
        with self._lock:
            self._proxies = list(proxies)
            self._cycle = itertools.cycle(self._proxies) if self._proxies else None
            self.enabled = bool(self._proxies)

    def next(self) -> Proxy | None:
        if not self._proxies:
            return None
        now = time.time()
        with self._lock:
            # try up to len() times to find a non-banned proxy
            for _ in range(len(self._proxies)):
                p = next(self._cycle)
                if p.banned_until <= now:
                    p.uses += 1
                    return p
            # all banned: return the one banned soonest
            return min(self._proxies, key=lambda x: x.banned_until)

    def report(self, p: Proxy | None, success: bool):
        if p is None:
            return
        with self._lock:
            if success:
                p.ok += 1
                p.fails = 0
            else:
                p.fails += 1
                if p.fails >= self.max_fails:
                    p.banned_until = time.time() + self.ban_seconds

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            return {
                "total": len(self._proxies),
                "banned": sum(1 for p in self._proxies if p.banned_until > now),
                "alive": sum(1 for p in self._proxies
                             if p.checked and p.ok > 0 and p.banned_until <= now),
                "dead": sum(1 for p in self._proxies if p.checked and p.ok == 0),
                "enabled": self.enabled,
            }
