from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_current_user
from .config import settings
from .rate_limit import RateLimiter
from .runners.python_runner import run_python
from .runners.sql_runner import run_sql
from .schemas import RunRequest, RunResponse

app = FastAPI(
    title="Academy-Tech Compiler API",
    description="Sandboxed Python/SQL execution service for academy-tech.ir",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

limiter = RateLimiter(limit=settings.rate_limit_per_minute, window_seconds=60)

# Registry of supported languages. Add a language by writing a new
# runner module and registering it here (see README: Adding a new language).
RUNNERS = {
    "python": run_python,
    "sql": run_sql,
}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "languages": sorted(RUNNERS.keys())}


@app.post("/api/run", response_model=RunResponse)
def run_code(req: RunRequest, request: Request, user_id: str | None = Depends(get_current_user)) -> RunResponse:
    if req.language not in RUNNERS:
        raise HTTPException(status_code=400, detail=f"Unsupported language '{req.language}'")

    if len(req.code) > settings.max_code_length:
        raise HTTPException(status_code=413, detail=f"Code too long (max {settings.max_code_length} characters)")

    client_ip = request.client.host if request.client else "unknown"
    rate_key = user_id or client_ip
    if not limiter.allow(rate_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment before running again.")

    result = RUNNERS[req.language](req.code)

    return RunResponse(
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
    )
