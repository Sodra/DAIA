FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* /app/
RUN uv sync --no-cache

COPY src /app/src
COPY config /app/config

RUN mkdir -p /app/data

CMD ["python", "-m", "daia"]
