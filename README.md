# Academy-Tech Compiler

**A professional, embeddable online Python/SQL code runner for the
[academy-tech.ir](https://academy-tech.ir) account-profile page.**

Students switch between languages, write code in the browser, click
Run, and see the output — all inside a Docker-sandboxed backend built
for untrusted, arbitrary code execution.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/A-Babaei/academy-tech-compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/A-Babaei/academy-tech-compiler/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](backend/requirements.txt)
[![No MATLAB license required](https://img.shields.io/badge/MATLAB-not%20required-lightgrey.svg)](#why-python--sql-not-matlab)

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Why Python + SQL, not MATLAB](#why-python--sql-not-matlab)
- [Features](#features)
- [Demo](#demo)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start-local-testing)
- [Deploying to production](#deploying-to-production)
- [Integrating into the account-profile page](#integrating-into-the-account-profile-page)
- [Environment variables](#environment-variables)
- [Adding a new language](#adding-a-new-language)
- [Testing](#testing)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why this exists

academy-tech.ir wanted a compiler/runner students could use directly
from their account-profile page — no separate tool, no install, switch
language and go. This repository is that feature: a small, self-hosted
service you own end-to-end, instead of embedding a third-party code
runner (with its own tracking, uptime, and data-handling risks) inside
a logged-in area of your site.

## Why Python + SQL, not MATLAB

MATLAB is commercial software from MathWorks and requires a paid
license per seat/server. Redistributing MATLAB, bundling a MATLAB
runtime, or running MATLAB code on your server on students' behalf
**without a valid MathWorks license would violate MathWorks' license
terms and copyright law.** This project deliberately does **not**
include, emulate, or require MATLAB.

Instead it ships **Python** (CPython, PSF license — free) and **SQL**
(executed against an ephemeral in-memory SQLite engine, public domain —
free). Both give students a genuinely useful "compiler" experience with
zero licensing risk to you.

If you later want MATLAB-*like* scripting, the legally clean option is
[GNU Octave](https://octave.org/) (GPL, free, MATLAB-compatible syntax
for most basic scripts). The architecture is intentionally built so a
third `octave` language can be registered later in a few hours of work
(see [Adding a new language](#adding-a-new-language)) — it is **not**
included by default, exactly as requested.

## Features

- **Switchable language tabs** — Python and SQL today, one file away
  from a third.
- **Real sandboxing, not a toy `eval`** — every run is a throwaway
  Docker container: no network, read-only filesystem, non-root user,
  all Linux capabilities dropped, hard memory/CPU/process-count caps,
  and a wall-clock timeout.
- **Per-user auth** — every run is tied to a signed, short-lived JWT
  identifying the logged-in academy-tech.ir user; no anonymous
  execution in production.
- **Rate limiting** built in, per user (falls back to per-IP).
- **Zero-dependency frontend** — vanilla JS and CSS, no CDN calls, no
  third-party trackers, nothing for a browser extension or ad-blocker
  to fight with.
- **Stack-agnostic** — the widget is a `<div>` plus two static files;
  it doesn't care whether academy-tech.ir runs WordPress, Django,
  Node, or something else. A ready WordPress example is included.
- **Extensible by design** — adding a language is: write a runner
  module, register it, rebuild the sandbox image if it needs a new
  interpreter. Auth, rate limiting, and sandboxing code never change.
- **Documented threat model** — [SECURITY.md](SECURITY.md) spells out
  exactly what's defended against and what you still need to configure.

## Demo

```
┌───────────────────────────────────────────────────────┐
│ [ Python ]  SQL                                        │
├───────────────────────────────────────────────────────┤
│ 1  print("hello, academy-tech")                        │
│ 2                                                       │
├───────────────────────────────────────────────────────┤
│ [ Run ]  [ Clear ]                          exit 0 · 41ms │
├───────────────────────────────────────────────────────┤
│ Output                                                  │
│ hello, academy-tech                                     │
└───────────────────────────────────────────────────────┘
```

Open `frontend/demo.html` after starting the backend
(`docker compose up --build`) to try it locally in a real browser.

## Architecture

```
┌───────────────────────────┐        ┌──────────────────────────────┐
│  account-profile page      │        │        Compiler API           │
│  (academy-tech.ir)         │  HTTPS │        (this repo, backend/)  │
│                             ├───────►│  FastAPI, JWT-authenticated,  │
│  <div id="academy-tech-    │        │  rate-limited                 │
│   compiler" data-token=…>  │        │                                │
│  widget.js + widget.css    │        └───────────────┬────────────────┘
└───────────────────────────┘                         │ docker API
                                                        │ (via socket-proxy,
                                                        │  never the raw socket)
                                                ┌───────▼────────────────┐
                                                │  Sandbox container      │
                                                │  (backend/sandbox/)     │
                                                │  no network, read-only  │
                                                │  fs, dropped caps,      │
                                                │  memory/cpu/pids caps,  │
                                                │  removed after each run │
                                                └──────────────────────────┘
```

- **`frontend/`** — zero-dependency, vanilla-JS widget. Drop two files
  (`widget.js`, `widget.css`) on your own static hosting/CDN and embed
  a `<div>` on the profile page.
- **`backend/app/`** — FastAPI service exposing `POST /api/run`.
  Verifies a JWT issued by your main site, rate-limits per user, and
  dispatches the run to an isolated Docker container.
- **`backend/sandbox/`** — the locked-down image that actually
  executes student code. Built once, reused for every run.
- **`examples/`** — copy-paste integration snippets (generic HTML, and
  a WordPress shortcode example, since many Iranian academy sites run
  WordPress — swap for your actual stack).

See [SECURITY.md](SECURITY.md) for the full threat model and hardening
checklist before going to production.

## Repository layout

```
academy-tech-compiler/
├── backend/
│   ├── app/                 FastAPI service (auth, rate limiting, API)
│   │   ├── runners/         one module per supported language
│   │   ├── config.py
│   │   ├── sandbox.py       shared Docker-execution logic
│   │   └── main.py
│   ├── sandbox/              image that actually runs student code
│   │   ├── Dockerfile
│   │   └── runners/run_sql.py
│   ├── tests/                 pytest unit tests
│   └── requirements.txt
├── frontend/
│   ├── widget.js              embeddable widget, zero dependencies
│   ├── widget.css
│   └── demo.html               local test page
├── examples/
│   ├── embed-snippet.html      generic integration snippet
│   └── wordpress-shortcode.php example JWT issuance for WordPress
├── docker-compose.yml
├── .env.example
├── SECURITY.md
└── README.md
```

## Quick start (local testing)

Requires Docker Engine ≥ 24 and Python ≥ 3.11 on the machine you deploy to.

```bash
# 1. Build the sandbox image students' code actually runs inside
docker build -t academy-tech-compiler-sandbox:latest ./backend/sandbox

# 2. Configure secrets
cp .env.example .env
# edit .env: set JWT_SECRET to a long random value (openssl rand -hex 32)

# 3. Run the stack (API + a locked-down docker-socket-proxy, see SECURITY.md)
docker compose up --build

# 4. Open the demo page (uses a dev token, ALLOW_ANONYMOUS=true only for local testing)
#    frontend/demo.html — open directly in a browser, or serve it with any static server
```

The API listens on `http://localhost:8000`. Health check:

```bash
curl http://localhost:8000/api/health
```

## Deploying to production

1. **Run this on its own small VM/container host**, separate from your
   main web server and database. It executes arbitrary student code —
   isolate the blast radius (see [SECURITY.md](SECURITY.md)).
2. Build and pin the sandbox image (`docker build ... && docker tag ...`
   with a specific digest, not just `:latest`, once you're happy with it).
3. Set real environment variables (`.env` or your platform's secret
   manager) — **never commit `.env`** (it's already in `.gitignore`).
4. Put the API behind HTTPS (e.g. Nginx/Caddy reverse proxy or your
   cloud provider's load balancer) with a certificate for
   `compiler-api.academy-tech.ir` (or whatever subdomain you choose).
5. Set `ALLOWED_ORIGINS=https://academy-tech.ir` (comma-separate if you
   have staging/www variants) and `ALLOW_ANONYMOUS=false`.
6. Host `frontend/widget.js` / `widget.css` on your own domain/CDN (not
   a third-party CDN) and reference them from the profile page.
7. Wire up JWT issuance: your existing site backend (WordPress/PHP,
   Django, Node, whatever academy-tech.ir runs on) must sign a
   short-lived token (`sub` = logged-in user id) when it renders the
   profile page. See [`examples/`](examples/).

## Integrating into the account-profile page

The widget is framework-agnostic — it's a `<div>` plus two static
files. Your site backend only needs to do one thing: **render a
short-lived JWT for the currently logged-in user** into the page.

```html
<div
  id="academy-tech-compiler"
  data-api-url="https://compiler-api.academy-tech.ir"
  data-token="{{ SERVER_RENDERED_JWT_FOR_THIS_USER }}"
  data-default-language="python"
></div>
<link rel="stylesheet" href="/compiler/widget.css">
<script src="/compiler/widget.js" defer></script>
```

A ready-to-adapt WordPress example (shortcode + JWT issuance) is in
[`examples/wordpress-shortcode.php`](examples/wordpress-shortcode.php).
If academy-tech.ir runs on something else, the same pattern applies —
only the JWT-issuing snippet changes; the widget and API stay
identical, which is what makes it "switchable" across stacks.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET` | — (required) | HMAC secret shared with your main site to verify user tokens |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_AUDIENCE` | `academy-tech-compiler` | Expected `aud` claim |
| `ALLOWED_ORIGINS` | `https://academy-tech.ir` | CORS allow-list, comma-separated |
| `ALLOW_ANONYMOUS` | `false` | Dev-only: skip auth. **Never `true` in production.** |
| `RUN_TIMEOUT_SECONDS` | `8` | Hard wall-clock limit per run |
| `MAX_OUTPUT_BYTES` | `65536` | Output truncation limit |
| `MAX_CODE_LENGTH` | `20000` | Max submitted code length (characters) |
| `RATE_LIMIT_PER_MINUTE` | `10` | Runs allowed per user/IP per minute |
| `SANDBOX_IMAGE` | `academy-tech-compiler-sandbox:latest` | Image used to execute code |
| `SANDBOX_MEM_LIMIT` | `128m` | Per-run memory cap |
| `SANDBOX_NANO_CPUS` | `500000000` (0.5 CPU) | Per-run CPU cap |
| `SANDBOX_PIDS_LIMIT` | `64` | Per-run process count cap |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | Set to the socket-proxy URL in production, see SECURITY.md |

## Adding a new language

The runner interface is intentionally small:

1. Add `backend/app/runners/<lang>_runner.py` exposing `run_<lang>(code: str) -> RunResult`,
   calling `run_in_sandbox(files=..., cmd=..., timeout=..., max_output_bytes=...)`.
2. Register it in the `RUNNERS` dict in `backend/app/main.py`.
3. If the language needs an interpreter not already in the sandbox image,
   add it to `backend/sandbox/Dockerfile` and rebuild.
4. Add the tab to `frontend/widget.js`'s `LANGUAGES` list.

This is how you'd add Octave later, or any other free/open-source
language, without touching the auth, rate-limiting, or sandboxing code.

## Testing

```bash
cd backend
pip install -r requirements.txt pytest
pytest -q
```

Unit tests cover request validation and rate limiting. End-to-end
sandbox execution requires a real Docker daemon and is exercised by
`docker build` in CI (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml))
— test it live with `docker compose up` before pointing production
traffic at it.

## Security

This service executes **untrusted, arbitrary code submitted by website
visitors** — that's treated as the primary threat throughout the
design: no network access from inside the sandbox, read-only
filesystem, non-root execution, dropped capabilities, resource and
time limits, per-request ephemeral containers, JWT-gated access, and a
docker-socket proxy instead of a raw socket mount. Full threat model,
what's covered, what isn't, and a pre-launch checklist live in
[SECURITY.md](SECURITY.md) — read it before deploying to
academy-tech.ir. If you find a vulnerability, please report it
privately rather than filing a public issue (see
[SECURITY.md → Reporting a vulnerability](SECURITY.md#reporting-a-vulnerability)).

## Roadmap

- [ ] Optional GNU Octave runner (MATLAB-compatible syntax, GPL, no
      license fee) as an opt-in third language.
- [ ] Redis-backed rate limiter for multi-replica deployments.
- [ ] Signed, downloadable run history per user (nice-to-have for
      grading/homework use cases).
- [ ] Optional gVisor/Kata runtime for stronger kernel isolation.

Contributions toward any of these are welcome — see below.

## Contributing

Issues and pull requests are welcome. Before opening a PR:

1. Run the test suite (`cd backend && pytest -q`).
2. Make sure `docker build ./backend/sandbox` still succeeds.
3. Keep the security properties in [SECURITY.md](SECURITY.md) intact —
   any change touching `backend/app/sandbox.py` or
   `backend/sandbox/Dockerfile` gets extra scrutiny for a reason.

## License

Code in this repository is © A.Babaei and released under the
[MIT License](LICENSE) — you're free to use, modify, and deploy it for
academy-tech.ir or elsewhere. Third-party dependencies keep their own
licenses (see [SECURITY.md → Third-party components & licenses](SECURITY.md#third-party-components--licenses)).
No MATLAB/MathWorks code, binaries, or license keys are included or
required anywhere in this project.
