# Security

This service executes **untrusted, arbitrary code submitted by website
visitors**. Treat every request as hostile. This document explains the
threat model, the defenses actually implemented, and what you — the
deployer — must still configure before going live on academy-tech.ir.

## Threat model

- A logged-in (or, if misconfigured, anonymous) user submits Python or
  SQL intending to: exhaust server resources, break out of the sandbox,
  read/exfiltrate data, attack other users, or attack academy-tech.ir's
  own infrastructure from inside your network.
- The widget's output is untrusted text and must never be rendered as
  HTML in the browser.

## Defenses implemented here

**Execution isolation (per run, both languages):**
- Runs inside a purpose-built Docker container (`backend/sandbox/`), one
  container per run, destroyed immediately after.
- `network_disabled=True` — no network access at all from inside the
  sandbox (no exfiltration, no calling out, no pivoting to internal
  services).
- `read_only=True` root filesystem; only `/tmp` is writable, mounted as
  `tmpfs` with `noexec,nosuid`, capped at 16 MB.
- Runs as a fixed **non-root, unprivileged** user (uid `65532`).
- `cap_drop=["ALL"]` and `no-new-privileges:true` — no Linux capabilities,
  no privilege escalation via setuid binaries.
- Hard caps on memory (`SANDBOX_MEM_LIMIT`, default 128 MB), CPU
  (`SANDBOX_NANO_CPUS`, default 0.5 core), and process/thread count
  (`SANDBOX_PIDS_LIMIT`, default 64) — mitigates fork-bombs and resource
  exhaustion.
- Wall-clock timeout (`RUN_TIMEOUT_SECONDS`, default 8s) enforced by the
  API, which kills and force-removes the container if exceeded.
- Output is truncated (`MAX_OUTPUT_BYTES`) before ever reaching the
  browser, and code length is capped (`MAX_CODE_LENGTH`) before a
  container is even created.
- SQL runs against a **fresh in-memory SQLite database per request**
  (`sqlite3.connect(":memory:")`), inside the same locked-down container
  above — there is no real database to damage, and even the in-memory DB
  is discarded when the container is removed.

**API-level:**
- Every `POST /api/run` requires a valid, signed JWT (`Authorization:
  Bearer <token>`) issued by your main site, identifying the user
  (`sub` claim). `ALLOW_ANONYMOUS` exists only for local development and
  must be `false` in production.
- Per-user (falling back to per-IP) rate limiting (`RATE_LIMIT_PER_MINUTE`).
  The default in-process limiter is fine for a single instance; if you
  scale to multiple API replicas, swap it for a shared store (Redis) —
  see the `RateLimiter` class in `backend/app/rate_limit.py`, it's a
  drop-in interface.
- CORS restricted to `ALLOWED_ORIGINS` — only your own domain(s) can call
  the API from a browser.
- The frontend widget writes all API output using `textContent`, never
  `innerHTML`, so nothing a student's program prints can inject HTML/JS
  into the page (stored/reflected XSS via output is not possible through
  this code path).

**Docker daemon access:**
- The API container never mounts `/var/run/docker.sock` directly — that
  is root-equivalent access to the whole host and is a common way these
  projects get "run code inline" security fatally wrong.
- Instead, `docker-compose.yml` fronts the real socket with
  [`tecnativa/docker-socket-proxy`](https://github.com/Tecnativa/docker-socket-proxy),
  configured to allow only the specific Docker API calls the backend
  needs (`CONTAINERS`, `IMAGES`, `POST`) and nothing else (no `EXEC`, no
  `VOLUMES`, no `NETWORKS` management, no daemon-wide `INFO` beyond
  health).

## What you must still do before production

None of the above matters if the surrounding deployment is careless.
Before pointing academy-tech.ir traffic at this:

1. **Run it on an isolated host/VM**, not the same machine as your main
   database or admin panel. If the sandbox is ever escaped, the blast
   radius should stop at that VM.
2. **Keep the sandbox image current** — rebuild periodically
   (`docker build --pull`) to pick up base-image (`python:3.11-slim`)
   security patches. Pin by digest once satisfied, and re-pin
   deliberately, not automatically.
3. **Put TLS in front of the API** (Nginx/Caddy/your cloud LB) —
   `Authorization: Bearer` tokens must never travel over plain HTTP.
4. **Generate a strong `JWT_SECRET`** (`openssl rand -hex 32`) and store
   it in a secret manager / environment variable, never in source
   control. Rotate it if you ever suspect exposure.
5. **Issue short-lived tokens** (a few minutes) from your main site on
   each page render, scoped to that one user — don't hand out long-lived
   tokens the widget stores client-side.
6. **Consider stronger kernel isolation** for defense-in-depth if this
   ever needs to run more permissive workloads: gVisor (`runsc`) or
   Kata Containers as the container runtime tighten the syscall surface
   beyond stock `runc`. Not required for the Python-stdlib/SQLite
   scope shipped here, but worth it if you expand what languages/packages
   are allowed.
7. **Monitor and alert**: log `exit_code`, `timed_out`, and rate-limit
   rejections; alert on sustained abuse from one user/IP.
8. **Add a CDN/WAF** (e.g. Cloudflare) in front of the public API for
   DDoS protection and an extra layer of bot filtering, independent of
   the app-level rate limiter.
9. **Backups/segregation**: this service should have no credentials to
   your main site's database. It doesn't need any, and none are wired
   in — keep it that way.

## Residual risk, explicitly

- A user could `ATTACH DATABASE` to a path inside the sandbox's own
  ephemeral `tmpfs` from SQL — this writes only to a 16 MB, `noexec`,
  throwaway filesystem that's destroyed with the container. Accepted.
- Stock `runc` container isolation is strong but not equivalent to a
  hardware VM boundary. If you need that level of assurance, adopt
  gVisor/Kata (see above) — the app code doesn't need to change.
- The in-process rate limiter resets on API restart and doesn't
  coordinate across replicas. Fine for a single instance; swap for
  Redis if you scale out.

## Reporting a vulnerability

If you (or anyone else) find a security issue in this repository, please
open a private report via GitHub's "Report a vulnerability" flow on this
repo, or email the address listed on the maintainer's GitHub profile,
rather than filing a public issue.

## Third-party components & licenses

| Component | License | Notes |
|---|---|---|
| CPython | PSF License | Interpreter used inside the sandbox |
| SQLite (via Python's `sqlite3` stdlib module) | Public domain | In-memory only, per-request |
| FastAPI | MIT | API framework |
| PyJWT | MIT | Token verification |
| `docker` (Docker SDK for Python) | Apache-2.0 | Talks to the Docker API / socket-proxy |
| `sqlparse` | BSD-3-Clause | Safely splits multi-statement SQL input |
| `tecnativa/docker-socket-proxy` | MIT | Restricts Docker API exposure (used in `docker-compose.yml`, not vendored) |

No MATLAB, Simulink, MathWorks code, binaries, license files, or license
keys are included, vendored, or required anywhere in this repository.
