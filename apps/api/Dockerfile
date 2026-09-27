FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock ./

RUN pip install --no-cache-dir uv==0.10.9 \
    && uv sync --frozen --no-dev --no-install-project

COPY apps/api/app ./app

EXPOSE 8000

CMD ["sh", "-c", "exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
