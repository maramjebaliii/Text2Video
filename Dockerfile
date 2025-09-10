# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Configurable pip mirrors (default: Tsinghua as primary, PyPI as fallback)
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_EXTRA_INDEX_URL=https://pypi.org/simple

# Install system deps: ffmpeg (includes ffprobe) and Chinese fonts to avoid tofu
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# First copy dependency metadata and package sources to leverage cache and allow packaging
COPY pyproject.toml README.md /app/
COPY app /app/app

# Install python deps early to cache layers when code changes
RUN python -m pip install --upgrade pip \
    && pip config set global.index-url $PIP_INDEX_URL \
    && pip config set global.extra-index-url $PIP_EXTRA_INDEX_URL \
    && pip config set global.timeout 120 \
    && pip install .

# Now copy the rest of the source code (main.py, streamlit, tests, etc.)
COPY . /app

# Ensure output dir exists
RUN mkdir -p /app/output

# Entrypoint (script is added below in docker/entrypoint.sh)
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Note: you can mount a local config.yaml or .env into /app to override container config
# Example docker-compose mounts in repository: ./config.yaml:/app/config.yaml:ro and env_file: .env

EXPOSE 8000 8501

# api | ui
ENV RUN_MODE=api

CMD ["/entrypoint.sh"]
