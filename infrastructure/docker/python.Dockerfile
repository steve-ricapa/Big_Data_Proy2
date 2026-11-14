FROM python:3.11.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
RUN mkdir /app/checkpoints && chmod 0770 /app/checkpoints
COPY pyproject.toml README.md /app/
COPY requirements.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY src/ /app/src/
RUN pip install --no-cache-dir --no-deps .
COPY services/ /app/services/
ENV PYTHONPATH=/app/src
USER 10001:10001
CMD ["python", "-m", "threat_intelligence.cli", "--help"]

FROM runtime AS test
USER root
COPY requirements-mcp.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements-mcp.lock
RUN pip install --no-cache-dir pytest==9.2.0
COPY tests/ /app/tests/
USER 50000:0
ENTRYPOINT ["python", "-m", "pytest"]

FROM runtime AS mcp
USER root
COPY requirements-mcp.lock /app/
RUN pip install --no-cache-dir --require-hashes -r requirements-mcp.lock && pip check
USER 10001:10001
CMD ["python", "-m", "services.mcp_server.server"]
