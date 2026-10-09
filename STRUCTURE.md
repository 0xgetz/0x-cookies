# Project structure

A single-file-friendly Python project: no build step, no framework, standard library
first. Below is the annotated layout and the runtime data-flow.

```
0x-cookies/
│
├──  server.py              🖥️  Control panel — HTTP API + WebSocket live stats
├──  cli.py                 ⌨️  Headless runner (VPS / cron) — same engine, no UI
├──  start.sh               🚀  One-shot launcher: installs browser + system libs, starts panel
├──  gen_configs.py         🏭  Generates the 139 platform configs from the shared registry
├──  README.md              📘  Docs (this language) + 4 translations in docs/
├──  STRUCTURE.md           🗺️  This file
├──  CONTRIBUTING.md        🤝  How to add platforms / send PRs
├──  LICENSE                ⚖️  MIT
│
├──  core/                  ⚙️  The engine (imported by both server.py and cli.py)
│   ├──  config.py          ── OpenBullet-style config schema + validation
│   ├──  engine.py          ── Job runner: http + browser, retry, captures, stats
│   └──  proxies.py         ── Proxy parsing, rotation, auto-ban
│
├──  web/                   🎛️  Dashboard (single self-contained HTML, Tailwind CDN)
│   └──  index.html         ── Live stats, log, hits, inputs/config/proxy tabs
│
├──  configs/               📦  Job definitions
│   ├──  example_http.json  ── Raw HTTP request template
│   ├──  example_cookie.json── Browser cookie template
│   └──  platforms/         ── 139 ready per-platform configs (github.json, …)
│
├──  data/                  💾  Output directory (git-ignored)
│   ├──  hits.txt           ── valid results + captures
│   └──  all.txt            ── every result (valid / invalid / error)
│
├──  docs/                  🌍  Translations
│   ├──  README.id.md       ── Bahasa Indonesia
│   ├──  README.es.md       ── Español
│   ├──  README.zh.md       ── 中文
│   └──  README.ar.md       ── العربية (RTL)
│
└──  assets/                🎨  Branding
    ├──  logo.svg / .png    ── Hexagon + cookie emblem
    └──  banner.svg / .png  ── README banner
```

---

## Runtime data-flow

```
                ┌──────────────────────────────────────────────────────────┐
                │                       USER                                │
                │      browser (web panel)        terminal (CLI)            │
                └───────────────┬─────────────────────────┬───────────────┘
                                │ HTTP / WS               │ argv + files
                                ▼                         ▼
                 ┌───────────────────────┐     ┌───────────────────────┐
                 │      server.py        │     │        cli.py         │
                 │  ─ controls/hits API  │     │   (no web UI)         │
                 │  ─ WebSocket :port+1  │     └───────────┬───────────┘
                 └───────────┬───────────┘                 │
                             │        both import           │
                             └──────────────┬───────────────┘
                                            ▼
                       ┌────────────────────────────────────────────┐
                       │                 core/                       │
                       │                                            │
                       │   config.py ── validate & load a job        │
                       │        │                                    │
                       │        ▼                                    │
                       │   engine.py ── Job                          │
                       │      ┌──────────────┬──────────────┐       │
                       │      │  HTTP path   │  BROWSER path │       │
                       │      │  (fast)      │  (accurate)   │       │
                       │      └──────┬───────┴───────┬───────┘       │
                       │             │               │               │
                       │        proxies.py ── rotate + auto-ban      │
                       └─────────────┬───────────────┬──────────────┘
                                     │               │
                                     ▼               ▼
                            ┌──────────────┐  ┌──────────────────────┐
                            │  remote site │  │  headless Chromium   │
                            │  (requests)  │  │  (Playwright)        │
                            └──────┬───────┘  └──────────┬───────────┘
                                   │                     │
                                   └──────────┬──────────┘
                                              ▼
                             ┌─────────────────────────────────┐
                             │  verdict: valid / invalid /     │
                             │           error                 │
                             │  ⚠ fail rule WINS over success  │
                             └──────────────┬──────────────────┘
                                            ▼
                             ┌─────────────────────────────────┐
                             │  data/hits.txt · data/all.txt   │
                             │  live stats → panel (ws/poll)   │
                             └─────────────────────────────────┘
```

---

## Per-input isolation (why dead files can't look valid)

```
   inputs ──► ┌────────────┐   ┌────────────┐   ┌────────────┐
              │ context #1 │   │ context #2 │   │ context #3 │   each = its own
              │ cookies A  │   │ cookies B  │   │ cookies C  │   Playwright BrowserContext
              └─────┬──────┘   └─────┬──────┘   └─────┬──────┘   (no cookie leakage)
                    ▼                ▼                ▼
                verdict 1        verdict 2        verdict 3
```

## Detection modes

```
  redirect ── the site bounces anonymous users to /login
              → final URL tells the truth. Simple & precise.

  marker   ── a SPA that keeps you on the same URL when logged out
              → matched via valid/invalid DOM selectors + body markers.
              → can return "uncertain" when a signal is inconclusive.
```
