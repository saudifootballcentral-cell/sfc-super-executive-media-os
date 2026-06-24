# ============================================================
# SFC Super Executive Media OS — Railway Production Dockerfile
# Multi-stage build: deps → production
# ffmpeg + ffprobe included for Video Intelligence (live clipping)
# Safe defaults: LIVE_PUBLISHING_ENABLED=false
# ============================================================

# ---- Stage 1: dependency builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install third-party dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Install the sfc package — non-editable so it is copied into site-packages.
# An editable install (-e) writes a .pth file with the build-time absolute path,
# which breaks when the venv is copied into the production stage at a different path.
COPY src/ ./src/
COPY pyproject.toml .
RUN pip install --no-cache-dir .


# ---- Stage 2: production image ----
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="SFC Super Executive Media OS"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.description="Autonomous AI-native Saudi football media OS"

# Install ffmpeg + ffprobe (required by Video Intelligence for live clipping/enhancement)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1000 sfc \
    && useradd --uid 1000 --gid sfc --shell /bin/bash --create-home sfc

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Safe defaults — override via Railway environment variables
ENV LIVE_PUBLISHING_ENABLED=false
ENV GENERATE_REAL_ASSETS=false
ENV VIDEO_PROCESSING_ENABLED=false

WORKDIR /app

# Copy source
COPY src/ ./src/
COPY constitution/ ./constitution/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# Create runtime artifact directories owned by non-root user
RUN mkdir -p \
    artifacts/creative \
    artifacts/video_intelligence \
    artifacts/analytics_sync \
    && chown -R sfc:sfc /app/artifacts

# Switch to non-root user
USER sfc

# Health check — verifies ffmpeg, ffprobe, core imports, Buffer + Video Intelligence
HEALTHCHECK --interval=30s --timeout=15s --start-period=20s --retries=3 \
    CMD python scripts/healthcheck.py || exit 1

CMD ["python", "scripts/run_demo.py", "--scenario", "transfer"]
