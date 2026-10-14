<div align="center">

<img src="assets/banner.png" alt="0x Cookies" width="100%"/>

# 0x Cookies

**OpenBullet-style bulk cookie & session checker — powered by real Chromium.**

Bulk-check whether saved cookies / logins are still alive across **189 platforms**.
Unlike plain HTTP checkers, it drives a **real headless Chromium** (Playwright), so it
stays accurate on sites that always answer `HTTP 200` (Microsoft, social, SaaS, …).

[![Python](https://img.shields.io/badge/python-3.9%2B-34e5b0?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-Chromium-8b7cf6?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/)
[![Platforms](https://img.shields.io/badge/platforms-189-f5b642?style=flat-square)](#-built-in-platforms)
[![License](https://img.shields.io/badge/license-MIT-34e5b0?style=flat-square)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-8b7cf6?style=flat-square)](CONTRIBUTING.md)
[![Made by 0xgetz](https://img.shields.io/badge/by-0xgetz-9aa4b2?style=flat-square&logo=github)](https://github.com/0xgetz)

[**English**](README.md) · [Indonesia](docs/README.id.md) · [Español](docs/README.es.md) · [中文](docs/README.zh.md) · [العربية](docs/README.ar.md)

</div>

---

## Why this exists

Most cookie checkers send an HTTP request and look at the status code. That breaks the
moment a site returns `200 OK` for both a live **and** a dead session — you get 100%
"valid" on garbage. **0x Cookies** loads the page in a real browser, follows the
redirect, and decides from the **final URL + DOM** whether you are actually logged in.

- **Real browser verdicts** — headless Chromium via Playwright.
- **Isolated contexts** — each input runs in its own browser context, so cookies never
  leak between accounts and a dead file can never look valid.
- **Fail wins over success** — landing on a login/error page is always `invalid`.
- **189 ready platforms** — plus a generic HTTP + browser config engine.
- **Web control panel** — upload inputs/configs/proxies, start/pause/stop, live stats.
- **CLI runner** — same engine, perfect for a VPS or cron.
- **Proxy pool** — rotate and auto-ban on failure (`http/https/socks4/socks5`).

> **Authorized use only.** Test accounts you own or are explicitly allowed to test.
> See [Disclaimer](#️-disclaimer).

---

## Quick start

```bash
git clone https://github.com/0xgetz/0x-cookies.git
cd 0x-cookies
./start.sh                 # opens http://localhost:8080
```

`start.sh` installs Playwright, downloads Chromium, and pulls in the required system
libraries (apt / dnf / apk). Prefer to do it by hand?

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium     # Debian/Ubuntu
python server.py --host 0.0.0.0 --port 8080
```

> Open ports **8080** (panel) **and 8081** (WebSocket live stats) if you access the
> panel from another machine. If 8081 is blocked the dashboard falls back to polling.

---

## Using the control panel

1. **Inputs** — paste one per line, or upload a `.txt`.
   `userpass` mode → `user:pass`; `cookie` mode → the cookie blob (or a cookie-file path).
2. **Config** — paste JSON, pick a preset, or load one of 189 configs from
   `configs/platforms/<name>.json`.
3. **Proxies** *(optional)* — one per line:
   `host:port`, `user:pass@host:port`, `scheme://host:port`
   (`http` `https` `socks4` `socks5` `socks5h`). Auto-rotate + auto-ban.
4. **Options** — workers, timeout, retry, proxy-ban duration, headless on/off.
5. **Start** — watch tested / hits / invalid / errors / CPM / progress live.
6. Download **hits** (`data/hits.txt`) and **all results** (`data/all.txt`).

---

## Built-in platforms

**189 configurations** ship in [`configs/platforms/`](configs/platforms), covering
social, email, cloud, developer, finance, streaming, shopping and more — e.g.
`google` `microsoft` `github` `discord` `instagram` `tiktok` `netflix` `spotify`
`openai` `claude` `notion` `sentry` `datadog` `supabase` `huggingface` `bybit` `revolut` `doordash` `strava` …

Each is either a `redirect` check (the site bounces anonymous users) or a `marker`
check (SPA: matched via valid/invalid DOM selectors and body markers). Regenerate the
whole set with:

```bash
python gen_configs.py
```

---

## Config format (OpenBullet-style)

```json
{
  "name": "Site login check",
  "author": "0x Cookies",
  "type": "http",
  "input_format": "userpass",
  "request": {
    "url": "https://site.com/api/login",
    "method": "POST",
    "headers": { "Cookie": "<COOKIE>", "User-Agent": "Mozilla/5.0" },
    "body": "user=<USER>&pass=<PASS>"
  },
  "captures": [ { "name": "token", "regex": "\"token\"\\s*:\\s*\"([^\"]+)\"" } ],
  "success": { "status": [200], "body_regex": "\"ok\":true", "url_regex": "/dashboard" },
  "fail":    { "body_regex": "invalid|incorrect", "url_regex": "(login|signin)" },
  "retry": 1
}
```

| Field | Meaning |
|-------|---------|
| `type` | `http` = raw request · `browser` = load the page in Chromium |
| `input_format` | `line` · `userpass` · `cookie` |
| `request` | url / method / headers / body (HTTP only) |
| `captures` | regex captures written to the **hits** file |
| `success` / `fail` | `status` · `body_regex` · `url_regex` |
| template vars | `<USER>` `<PASS>` `<LINE>` `<COOKIE>` usable in url, headers, body **and** regexes |

**`fail` always beats `success`** — if the final URL matches a login/error page the
result is `invalid`, no matter what else matched.

---

## CLI

```bash
# HTTP config
python cli.py --config configs/example_http.json --inputs users.txt \
  --proxies proxies.txt --workers 8 --timeout 30 \
  --hits hits.txt --all all.txt

# browser cookie check using a built-in platform
python cli.py --config configs/platforms/github.json --inputs cookies/ \
  --workers 4 --headful
```

---

## REST API

| Method | Path | Body |
|--------|------|------|
| `POST` | `/api/inputs` | `{"text":"a\nb"}` or `{"lines":[...]}` |
| `POST` | `/api/config` | `{"raw":"<json>"}` or a config object |
| `POST` | `/api/proxies` | `{"text":"host:port\n..."}` |
| `POST` | `/api/start` | `{"workers":4,"timeout":30,"retry":1,"headless":true}` |
| `POST` | `/api/stop` · `/api/pause` · `/api/resume` | — |
| `GET` | `/api/stats` | stats + log |
| `GET` | `/api/hits` · `/api/all` | results (text) |
| `WS` | `ws://host:8081/` | pushes stats + log every 0.5s |

Set `OXC_TOKEN` to require the `X-Auth-Token` header on every `POST`.

---

## Project structure

See **[STRUCTURE.md](STRUCTURE.md)** for the full annotated diagram.

```
0x-cookies/
├── server.py          control panel (HTTP + WebSocket live stats)
├── cli.py             headless runner
├── start.sh           one-shot launcher (installs browser + libs)
├── gen_configs.py     generate the 189 platform configs
├── core/              config · engine · proxies
├── web/               dashboard UI
├── configs/           example + per-platform configs
├── docs/              5 translated READMEs
└── assets/            logo + banner
```

---

## VPS without root (manual Chromium libs)

If `apt` is unavailable and Chromium fails with
`error while loading shared libraries: libglib-2.0.so.0`:

```bash
mkdir -p third_party/lib
cp /path/to/*.so* third_party/lib/   # collect the missing .so files
./start.sh                            # start.sh adds third_party/lib to LD_LIBRARY_PATH
```

---

## Contributing

Issues and PRs are welcome — new platform configs especially. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 0x Cookies

## ⚠️ Disclaimer

This tool is provided for **legitimate security research and testing accounts you own
or are explicitly authorized to test**. You are solely responsible for how you use it.
Never use it against systems or accounts without permission.

---

<div align="center">

Made by **0x Cookies** · [GitHub @0xgetz](https://github.com/0xgetz) · [Telegram @xiyyyyz](https://t.me/xiyyyyz)

</div>
