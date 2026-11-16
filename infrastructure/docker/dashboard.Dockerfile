# Build runner/runtime first. A separate tag lets dashboard updates preserve
# the running API/MCP images and makes the release survive coordinated backups.
ARG APP_IMAGE=ti-app:local
FROM ${APP_IMAGE}
USER root
COPY services/dashboard/app.py /app/services/dashboard/app.py
USER 10001:10001
