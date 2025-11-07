FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry --no-cache-dir \
    && poetry install --no-cache

COPY panel_app/ ./panel_app/
EXPOSE 5006