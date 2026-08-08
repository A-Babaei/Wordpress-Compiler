from ..config import settings
from ..sandbox import RunResult, run_in_sandbox


def run_python(code: str) -> RunResult:
    return run_in_sandbox(
        files={"main.py": code},
        # -I: isolated mode (ignores PYTHONPATH/user site-packages/env vars)
        # -B: don't write .pyc files (root fs is read-only anyway)
        cmd=["python", "-I", "-B", "/sandbox/main.py"],
        timeout=settings.run_timeout_seconds,
        max_output_bytes=settings.max_output_bytes,
    )
