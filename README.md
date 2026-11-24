# fantasy-basketball-analyzer-v2

Runs on waynezhu.dev. Made with [create-new-app](https://github.com/waynezhu6/create-new-app).

## Layout

- `backend/`: the API, in Python 3.13 (FastAPI, uv, PostgreSQL with psycopg 3), served at `waynezhu.dev/api/fantasy-basketball-analyzer-v2/`.
- `frontend/`: the web app (React 19, Vite, TypeScript), served at `waynezhu.dev/apps/fantasy-basketball-analyzer-v2/`.
- Infra: Docker, Caddy (via [infrastructure](https://github.com/waynezhu6/infrastructure)), GHCR.

## Deploying

Merging to `main` deploys. No deploy secrets are needed. CI builds one image with the backend and the built frontend, pushes it to GHCR, and asks the server's deployer to run it (infrastructure's `actions/deploy`). The deploy step proves which repo it is with a GitHub OIDC token, so the server only lets this repo deploy this app. Its output, including the backend's health check, streams into the Actions log, and a failed health check rolls back to the previous version. The app has to be registered in infrastructure first (Actions → Register app there); the deploy fails with a clear message until it is.

**What the app gets from the server** is declared in `infra.yml`, sent with every deploy. It starts as `postgres: true`: the first deploy creates the app's database and the backend gets `DATABASE_URL`. The server creates what's declared and missing, never removes anything, and refuses unknown settings; the settings are listed in infrastructure's README.

**App secrets** (API keys) go in this repo's Actions secrets (Settings → Secrets and variables → Actions), each listed as a `NAME=${{ secrets.NAME }}` line under `env` in the Deploy step of `.github/workflows/deploy.yml`; the backend gets it as the environment variable `NAME`. They must be single-line, and `DATABASE_URL`, `NODE_ENV` and `PORT` are reserved.

## Local dev

```bash
docker compose -f docker-compose.dev.yml up -d   # local Postgres on 5432
cp backend/.env.example backend/.env
npm install
npm run dev                                      # backend on localhost:3001
```

Then open `http://localhost:5173/apps/<folder name>/`. Dev uses the production paths: the frontend is at `/apps/<name>/` and proxies `/api/<name>/...` to the backend as `/api/...`, as Caddy does. `<name>` is the checkout's folder name locally and the repo name in CI.
The backend runs with [uv](https://docs.astral.sh/uv/) (`brew install uv`), which installs its packages on first use. Add one with `cd backend && uv add pandas`, then commit `pyproject.toml` and `uv.lock`.

## Paths

The app is served under a prefix, so never hardcode `/` or `/api` URLs:

- Frontend: call the backend with `api('/things')` or `apiUrl('/things')` from `frontend/src/api.ts`. Assets and imports are handled by Vite's `base`.
- Backend: routes stay under `/api/*` (Caddy strips the prefix). For URLs the backend sends to the browser (redirects, links, cookie paths), use `API_BASE` and `APP_BASE` from `backend/app/paths.py`. Set cookies with `path=API_BASE` so they only go to this app's backend; all apps share one domain.

## Sign-in

Apps share one passkey sign-in, the [auth](https://github.com/waynezhu6/auth) service at `/apps/auth/`. Its session cookie reaches every app's backend, and the backend asks the service who it belongs to:

```python
from .auth import CurrentUser

@app.get("/api/notes")
async def notes(user: CurrentUser):
    ...  # key data on user.id
```

A route with a `CurrentUser` parameter (`backend/app/auth.py`) answers 401 when nobody is signed in. `MaybeUser` gives the user or `None`, for routes that work either way.

On a 401 the web frontend sends the browser to the sign-in page, which returns it here afterwards:

```ts
import { api, loginUrl } from './api'

const res = await api('/notes')
if (res.status === 401) location.assign(loginUrl())
```

`/api/me` answers with the signed-in user. Locally there's no auth service: `AUTH_DEV_USER` in `backend/.env` signs you in as that name, and removing it signs you out. Accounts are invite-only; see auth's README.

Callers that can't sign in, like a script, an iOS Shortcut, use an API key: make one for this app on auth's admin page and send it as `Authorization: Bearer wz_…`. The backend accepts it the same way, and the user's `key` holds the key's name (it's unset for a signed-in browser). A key made for another app is refused.

## Database migrations

```bash
cd backend
uv run python -m app.migrate create add-notes     # makes migrations/<timestamp>_add-notes.sql
uv run --env-file=.env python -m app.migrate up   # apply by hand; startup does it too
```

Migrations are plain SQL files, applied in name order, each in its own transaction. There are no down migrations; undo a change with a new one. Query the database through the pool in `backend/app/db.py`:

```python
from .db import pool

async with pool.connection() as conn:
    rows = await (await conn.execute("select * from notes where owner = %s", (user.id,))).fetchall()
```

Migrations run automatically on backend startup, before it takes requests. If one fails the backend exits, so the deploy fails its health check and the previous version keeps serving.

Deploys don't stop the app: the new version starts and migrates while the old one still serves, then takes over. So a migration must leave the schema usable by the previous version: add tables and columns freely, but drop or rename one only in a later deploy, once no shipped code uses it.
