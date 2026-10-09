"""
OpenBullet-style config (a simplified "stacker").

A config describes how to validate ONE input line (typically user:pass or a
cookie blob). It runs as a small pipeline of request blocks; each block can
capture values with regex and set success/fail conditions.

Config JSON schema
------------------
{
  "name": "Example Login Check",
  "author": "0x Cookies",
  "type": "http" | "browser",          # browser = Playwright page load
  "input_format": "userpass" | "cookie" | "line",
  "request": {
     "url": "https://site.com/login",  # supports <USER> <PASS> <LINE> vars
     "method": "GET" | "POST",
     "headers": {"Cookie": "<COOKIE>"},
     "body": "user=<USER>&pass=<PASS>"
  },
  "captures": [ {"name": "token", "regex": "csrf_token=(\\w+)"} ],
  "success": { "url_regex": "", "body_regex": "Dashboard", "status": [200] },
  "fail":    { "url_regex": "(login|signin)", "body_regex": "invalid password" },
  "retry": 1
}

For "browser" type the request block loads `url` (with cookies applied) and the
success/fail checks run against the final URL + page HTML. This is what makes
the checker accurate for sites that always return HTTP 200.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Rule:
    url_regex: str = ""
    body_regex: str = ""
    status: list[int] = field(default_factory=list)

    def matches(self, url: str, body: str, status: int | None) -> bool:
        if self.url_regex and not re.search(self.url_regex, url, re.I):
            return False
        if self.body_regex and not re.search(self.body_regex, body, re.I | re.S):
            return False
        if self.status and status not in self.status:
            return False
        return bool(self.url_regex or self.body_regex or self.status)


@dataclass
class Capture:
    name: str
    regex: str
    group: int = 1


@dataclass
class Config:
    name: str = "Custom"
    author: str = "0x Cookies"
    type: str = "http"          # http | browser
    input_format: str = "line"  # line | userpass | cookie
    method: str = "GET"
    url: str = ""
    headers: dict = field(default_factory=dict)
    body: str = ""
    captures: list[Capture] = field(default_factory=list)
    success: Rule = field(default_factory=Rule)
    fail: Rule = field(default_factory=Rule)
    retry: int = 1
    # browser-specific
    platform: str = ""          # reuse a platform from checker.py PLATFORMS

    @staticmethod
    def from_dict(d: dict) -> "Config":
        req = d.get("request", {})
        s = d.get("success", {}) or {}
        f = d.get("fail", {}) or {}
        return Config(
            name=d.get("name", "Custom"),
            author=d.get("author", "0x Cookies"),
            type=d.get("type", "http"),
            input_format=d.get("input_format", "line"),
            method=req.get("method", d.get("method", "GET")).upper(),
            url=req.get("url", d.get("url", "")),
            headers=req.get("headers", {}) or {},
            body=req.get("body", "") or "",
            captures=[Capture(c["name"], c["regex"], c.get("group", 1))
                      for c in d.get("captures", []) or []],
            success=Rule(s.get("url_regex", ""), s.get("body_regex", ""), s.get("status", []) or []),
            fail=Rule(f.get("url_regex", ""), f.get("body_regex", ""), f.get("status", []) or []),
            retry=int(d.get("retry", 1)),
            platform=d.get("platform", ""),
        )

    @staticmethod
    def load(path: Path) -> "Config":
        return Config.from_dict(json.loads(Path(path).read_text()))

    def validate(self) -> list[str]:
        errs = []
        if self.type not in ("http", "browser"):
            errs.append("type must be 'http' or 'browser'")
        if self.type == "http" and not self.url:
            errs.append("request.url is required for http configs")
        if self.type == "browser" and not (self.url or self.platform):
            errs.append("browser configs need url or platform")
        if not (self.success.url_regex or self.success.body_regex or self.success.status):
            errs.append("at least one success condition is required")
        return errs


def parse_input_line(line: str, fmt: str) -> dict:
    """Split an input line into variables usable in templates."""
    line = line.strip()
    out = {"LINE": line, "USER": "", "PASS": "", "COOKIE": line}
    if fmt == "userpass":
        if ":" in line:
            u, p = line.split(":", 1)
            out["USER"], out["PASS"] = u, p
    elif fmt == "cookie":
        out["COOKIE"] = line
    return out


def render(template: str, vars_: dict) -> str:
    if not template:
        return template
    for k, v in vars_.items():
        template = template.replace(f"<{k}>", v or "")
    return template
