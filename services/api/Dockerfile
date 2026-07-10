FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY signaldesk ./signaldesk
COPY data ./data

RUN useradd --create-home --uid 10001 signaldesk \
    && chown -R signaldesk:signaldesk /app
USER signaldesk

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "signaldesk.main:app", "--host", "0.0.0.0", "--port", "8000"]
