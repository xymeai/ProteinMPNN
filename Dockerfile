FROM nvidia/cuda:11.8.0-base-ubuntu22.04

WORKDIR /app

ENV \
    # keep (large) mypy cache outside of working tree
    MYPY_CACHE_DIR='/tmp/.mypy_cache' \
    # always flush output from python
    PYTHONUNBUFFERED=TRUE \
    # enable fault handler (print tracebacks even after segfault or NCCL errors).
    PYTHONFAULTHANDLER=1 \
    # Copy from the cache instead of linking since it's a mounted volume
    UV_LINK_MODE=copy

ADD . /app

# Install dependencies using the lockfile and settings
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT [ "python", "proteinmpnn.py"]