FROM python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS package

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 10001 changeops \
    && useradd --system --uid 10001 --gid changeops --home-dir /app changeops

WORKDIR /app
COPY requirements.lock ./
COPY --from=package /wheels /wheels
RUN python -m pip install --require-hashes --only-binary=:all: -r requirements.lock \
    && python -m pip install --no-deps /wheels/changeops-*.whl \
    && rm -rf /wheels

COPY alembic.ini ./
COPY migrations ./migrations

USER changeops
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]
CMD ["uvicorn", "changeops.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

FROM runtime-base AS development
USER root
COPY pyproject.toml README.md ./
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
RUN python -m pip install ".[dev]" \
    && chown -R changeops:changeops /app
USER changeops

FROM runtime-base AS production
