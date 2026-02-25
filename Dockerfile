# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

FROM python:3.13-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=true \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./

# Install uv and project dependencies
RUN pip install uv && \
    uv sync --frozen --no-install-project --no-dev --no-editable

COPY . /app
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Install graphviz for diagram rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends graphviz procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system app && \
    useradd app -g app -d /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Health check script
COPY ./docker-healthcheck.sh /usr/local/bin/docker-healthcheck.sh
RUN chmod +x /usr/local/bin/docker-healthcheck.sh

USER app

HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 CMD ["docker-healthcheck.sh"]
ENTRYPOINT ["microsoft.azure-diagram-mcp-server"]
