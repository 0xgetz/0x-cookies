# Contributing to 0x Cookies

Thanks for taking the time to contribute! This project stays useful because people add
platform configs and fix detection logic. Here is how to help.

## Ways to contribute

- **Add a platform config** — the highest-value contribution. Most sites just need a
  correct `success` / `fail` rule (see below).
- **Improve detection** — report or fix a config that returns a wrong verdict.
- **Fix bugs** in the engine, panel, CLI or proxy layer.
- **Improve docs / translations.**

## Adding a platform config

1. Create `configs/platforms/<name>.json` (lowercase, no spaces).
2. Prefer the smallest reliable signal:
   - `type: "browser"` with a `url` that only a logged-in user reaches.
   - `success.url_regex` matching the logged-in landing page.
   - `fail.url_regex` matching the login/redirect page.
3. **Verify both directions** before opening a PR:
   - a *dead* cookie must return `invalid`;
   - a *live* cookie must return `valid`.
   You can probe anonymously for the `fail` case:

   ```bash
   python cli.py --config configs/platforms/<name>.json --inputs sample.txt --workers 1
   ```

4. Keep `"author": "0x Cookies"` and `"retry": 1` unless the site needs otherwise.

> Remember the golden rule: **`fail` wins over `success`.** If the final URL lands on a
> login page the result is `invalid` regardless of everything else.

## Regenerating the platform set

`configs/platforms/` is generated from the shared registry. After adding entries run:

```bash
python gen_configs.py
```

## Development setup

```bash
pip install playwright
python -m playwright install chromium
python -m playwright install-deps chromium   # Debian/Ubuntu
python server.py --host 127.0.0.1 --port 8080
```

Manual test of a single run without the UI:

```bash
python cli.py --config configs/example_http.json --inputs /tmp/in.txt --workers 1
```

## Coding style

- Python 3, standard library first; avoid new heavy dependencies.
- Keep modules small and readable; prefer clarity over cleverness.
- Match the existing style in `core/` and `server.py`.

## Commit / PR checklist

- [ ] Tested with a dead cookie **and** a live cookie (or explained why one is impossible).
- [ ] No secrets, no real credentials, no personal data in the diff.
- [ ] Uses the tool only on accounts you own or are authorized to test.
- [ ] Short, focused commits with a clear message.

## Code of conduct

Be respectful. No harassment, no sharing of others' data, and no use of the project
against systems or accounts without authorization.
