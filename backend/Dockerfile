# Built from the repo root (context: .). One image carries the whole app: the
# backend runs from it, and the server's deployer copies the built frontend out
# of /app/frontend/dist.
FROM node:20.19-alpine AS frontend
# The repo name: the frontend is built for waynezhu.dev/apps/<APP>/.
ARG APP
WORKDIR /app
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/
RUN npm ci --workspace=frontend --include-workspace-root=false
COPY frontend frontend
RUN test -n "$APP" || { echo "Build with --build-arg APP=<repo name>" >&2; exit 1; }
RUN APP="$APP" npm run build --workspace=frontend

# Debian-based (not alpine) so data packages like numpy and pandas install from
# prebuilt wheels. The builder and the final image share a base, so the
# virtualenv copies over as is.
FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev

FROM python:3.13-slim
WORKDIR /app/backend
COPY --from=builder /app/backend/.venv .venv
COPY backend/app app
COPY backend/migrations migrations
COPY --from=frontend /app/frontend/dist /app/frontend/dist
# paths.py builds the app's public URLs (/api/<APP>, /apps/<APP>/) from this;
# the server doesn't pass the name in. NODE_ENV is the server's name for
# "production" for every app, whatever its language.
ARG APP
ENV NODE_ENV=production APP=$APP PATH=/app/backend/.venv/bin:$PATH PYTHONUNBUFFERED=1
# The app only reads its files, so it doesn't need root.
USER nobody
EXPOSE 3001
CMD ["python", "-m", "app"]
