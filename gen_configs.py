"""
Generate OpenBullet-style browser configs from the bundled platform registry
(189 platforms) so the same rules power every part of the project.

Usage:
    python gen_configs.py            # writes configs/platforms/*.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    from core import registry  # type: ignore
    checker = registry  # PLATFORMS lives here
except Exception as e:  # pragma: no cover
    print("core/registry.py not importable:", e)
    sys.exit(1)


def _clean_url_re(rx: str) -> str:
    """Drop a trailing empty alternation (e.g. '|)' -> ')') which would make the
    regex match every URL on the host."""
    import re
    if not rx:
        return rx
    return re.sub(r"\|\s*\)", ")", rx)


def build(platform_name: str, p) -> dict:
    cfg = {
        "name": f"{platform_name} — cookie/session check",
        "author": "0x Cookies",
        "type": "browser",
        "input_format": "line",
        "url": p.url,
        "success": {},
        "fail": {},
        "captures": [],
        "retry": 1,
    }
    # URL-based rules (works for redirect-mode platforms)
    inv = _clean_url_re(p.invalid_url_re)
    val = _clean_url_re(p.valid_url_re)
    if inv:
        cfg["fail"]["url_regex"] = inv
    if val:
        cfg["success"]["url_regex"] = val
    # body markers strengthen marker-mode platforms
    if p.valid_body_any:
        cfg["success"]["body_regex"] = "|".join(map(_esc, p.valid_body_any[:3]))
    if p.invalid_body_any:
        cfg["fail"]["body_regex"] = "|".join(map(_esc, p.invalid_body_any[:3]))
    if not cfg["success"]:
        cfg["success"] = {"url_regex": r".*"}
    return cfg


def _esc(s: str) -> str:
    import re
    return re.escape(s)


def main():
    outdir = HERE / "configs" / "platforms"
    outdir.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, p in checker.PLATFORMS.items():
        cfg = build(name, p)
        (outdir / f"{name}.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        n += 1
    print(f"wrote {n} configs to {outdir}")


if __name__ == "__main__":
    main()
