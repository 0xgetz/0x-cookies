"""
Command-line runner (no web UI needed) — for VPS/cron/headless.

Examples:
  python cli.py --config configs/example_cookie.json --inputs inputs.txt \
      --proxies proxies.txt --workers 8 --timeout 30 \
      --hits hits.txt --all all.txt

  # quick browser check reusing a built-in platform from the cookie-checker
  python cli.py --platform microsoft --inputs cookies/ --workers 4
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from core.config import Config
from core.engine import Job
from core.proxies import ProxyPool, load_proxies


def collect_inputs(path: str) -> list[str]:
    p = Path(path)
    if p.is_dir():
        out = []
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".txt", ".json"):
                out.append(str(f))
        return out
    return [l.strip() for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description="0x Cookies CLI runner")
    ap.add_argument("--config", help="config JSON path")
    ap.add_argument("--platform", help="use a built-in platform (browser cookie check)")
    ap.add_argument("--inputs", help="file with one input per line, or a folder of cookie files")
    ap.add_argument("--proxies", help="proxy list file")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--retry", type=int, default=0)
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--hits", default="hits.txt")
    ap.add_argument("--all", dest="all_out", default="all.txt")
    args = ap.parse_args()

    if args.config:
        cfg = Config.load(Path(args.config))
    elif args.platform:
        # cookie-file mode: treat each input path as a "line" holding a file path
        cfg = Config(name=f"cookie:{args.platform}", type="browser",
                     input_format="line",
                     url=_platform_url(args.platform))
    else:
        sys.exit("provide --config or --platform")

    lines = collect_inputs(args.inputs) if args.inputs else []
    if not lines:
        sys.exit("no inputs")

    plist = []
    if args.proxies:
        text = Path(args.proxies).read_text()
        plist, bad = load_proxies(text)
        print(f"[*] proxies: {len(plist)} valid, {len(bad)} invalid")
    pool = ProxyPool(plist)

    job = Job(config=cfg, lines=lines, workers=args.workers, timeout=args.timeout,
              headless=not args.headful, pool=pool,
              hits_path=Path(args.hits), all_path=Path(args.all_out),
              retry_on_fail=args.retry)
    job.stats.total = len(lines)
    asyncio.run(job.run())
    print(f"[=] done: valid={job.stats.valid} invalid={job.stats.invalid} "
          f"errors={job.stats.errors} cpm={job.stats.cpm:.1f}")
    print(f"[=] hits -> {args.hits}   all -> {args.all_out}")


def _platform_url(platform: str) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cookie-checker"))
    try:
        import checker  # type: ignore
        return checker.PLATFORMS[platform].url
    except Exception:
        return ""


if __name__ == "__main__":
    main()
