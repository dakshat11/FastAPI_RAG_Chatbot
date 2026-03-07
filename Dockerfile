# ── Stage 1: Builder ─────────────────────────────────────────────
# A separate stage just to install dependencies.
# Why? faiss-cpu and psycopg need build tools (gcc) to compile.
# We don't want gcc in the final image — it bloats the size and
# increases the attack surface.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install uv

# Copy dependency manifest BEFORE the application code.
# Key insight: Docker caches each layer. If only your code changes
# (not pyproject.toml), this layer is cached and packages are NOT
# reinstalled. This makes rebuilds fast — seconds instead of minutes.
COPY pyproject.toml ./

# Install all packages into a venv inside the image
RUN uv venv .venv && uv sync --no-dev

# ── Stage 2: Runtime ─────────────────────────────────────────────
# Start fresh from a clean slim image.
# Copy ONLY the installed venv from the builder — no gcc, no build tools.
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

# Put the venv's Python first in PATH so it's used by default
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]