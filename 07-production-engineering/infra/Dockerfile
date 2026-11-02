FROM python:3.12.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
WORKDIR /srv/researchops
COPY . .
RUN uv sync --frozen --no-dev --package research-service
RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /srv/researchops
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s CMD [".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD [".venv/bin/python", "-m", "uvicorn", "research_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "64", "--timeout-keep-alive", "5"]
