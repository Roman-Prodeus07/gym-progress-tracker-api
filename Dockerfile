FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app && \
    useradd --system --gid app app

COPY pyproject.toml README.md requirements.lock ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN PIP_CONSTRAINT=/app/requirements.lock \
    PIP_BUILD_CONSTRAINT=/app/requirements.lock \
    python -m pip install --no-cache-dir .

USER app

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
