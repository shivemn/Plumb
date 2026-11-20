# Plumb's web API and its worker, in one container.
#
#   docker build -t plumb .
#   docker run -p 8000:7860 -e PLUMB_MODEL=... -e OPENROUTER_API_KEY=... plumb
#
# Settings are environment variables; `plumb serve --help` lists them. Without
# PLUMB_MODEL the server still analyses repos, and visitors write the report
# with their own key. Data (the job table, caches) goes to /data.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.32

FROM ${UV_IMAGE} AS uv

# Install the locked dependencies first, so a code change does not redo them.
FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/plumb
WORKDIR /src
COPY core/pyproject.toml core/uv.lock core/README.md ./
RUN uv sync --locked --no-dev --extra server --no-install-project
COPY core/src ./src
RUN uv sync --locked --no-dev --extra server --no-editable

FROM ${PYTHON_IMAGE}
# git clones the repos; nothing else is added to the base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 plumb \
    && mkdir -p /data \
    && chown plumb /data
COPY --from=build /opt/plumb /opt/plumb
ENV PATH=/opt/plumb/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PLUMB_HOME=/data \
    PORT=7860
USER plumb
WORKDIR /home/plumb
VOLUME /data
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/api/health', timeout=4)"]
CMD ["plumb", "serve", "--host", "0.0.0.0"]
