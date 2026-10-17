FROM ghcr.io/astral-sh/uv:0.9.5 AS uv
FROM python:3.12.12-slim-bookworm

COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app/pipeline
COPY pipeline/pyproject.toml pipeline/uv.lock ./
RUN uv sync --frozen --no-dev --extra db --no-extra capture --no-install-project
COPY pipeline/src ./src
# Keep the editable source layout: repo_root() locates replay fixtures from it.
RUN uv sync --frozen --no-dev --extra db --no-extra capture \
    && useradd --create-home --uid 10001 routine \
    && mkdir -p /app/.data/replays /app/.data/cache \
    && chown -R routine:routine /app/.data
COPY tests/scenarios /app/tests/scenarios
ENV PATH="/app/pipeline/.venv/bin:$PATH" API_CACHE_DIR=/app/.data/cache
USER routine
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "routine_watch.api:app", "--host", "0.0.0.0", "--port", "8000"]
