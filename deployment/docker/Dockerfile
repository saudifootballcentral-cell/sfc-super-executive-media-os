# ============================================================
# SFC Super Executive Media OS — Dockerfile
# Multi-stage build: deps → production
# ============================================================

# ---- Stage 1: dependency builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a venv for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: production image ----
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="SFC Super Executive Media OS"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.description="Autonomous AI-native Saudi football media OS"

# Non-root user for security
RUN groupadd --gid 1000 sfc && useradd --uid 1000 --gid sfc --shell /bin/bash --create-home sfc

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Repo root so constitution.py and prompt_loader.py resolve files correctly
ENV SFC_REPO_ROOT=/app

WORKDIR /app

# Copy source
COPY src/ ./src/
COPY constitution/ ./constitution/
COPY prompts/ ./prompts/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER sfc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "from sfc.graph.graph import build_graph; build_graph(); print('healthy')" || exit 1

# Default command: run demo
CMD ["python", "scripts/run_demo.py", "--scenario", "transfer"]
