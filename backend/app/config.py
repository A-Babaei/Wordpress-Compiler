"""Runtime configuration, read from environment variables.

Kept dependency-free (plain dataclass) rather than pydantic-settings so
the required environment surface is easy to read top-to-bottom.
"""
import os
from dataclasses import dataclass, field


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Settings:
    docker_host: str = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    sandbox_image: str = os.getenv("SANDBOX_IMAGE", "academy-tech-compiler-sandbox:latest")

    allowed_origins: list = field(
        default_factory=lambda: _split_csv(os.getenv("ALLOWED_ORIGINS", "https://academy-tech.ir"))
    )

    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "academy-tech-compiler")

    allow_anonymous: bool = os.getenv("ALLOW_ANONYMOUS", "false").lower() == "true"

    run_timeout_seconds: int = int(os.getenv("RUN_TIMEOUT_SECONDS", "8"))
    max_output_bytes: int = int(os.getenv("MAX_OUTPUT_BYTES", "65536"))
    max_code_length: int = int(os.getenv("MAX_CODE_LENGTH", "20000"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

    sandbox_mem_limit: str = os.getenv("SANDBOX_MEM_LIMIT", "128m")
    sandbox_nano_cpus: int = int(os.getenv("SANDBOX_NANO_CPUS", "500000000"))
    sandbox_pids_limit: int = int(os.getenv("SANDBOX_PIDS_LIMIT", "64"))


settings = Settings()
