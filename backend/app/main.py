from contextlib import asynccontextmanager

from fastapi import FastAPI

from .auth import CurrentUser, User, client
from .db import pool
from .migrate import migrate


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Don't take traffic until the schema is current. A failed migration stops
    # startup, so the deploy fails its health check instead of serving on a
    # stale schema.
    migrate()
    await pool.open()
    yield
    await pool.close()
    await client.aclose()


# Routes go under /api (Caddy strips /api/<name> to /api). FastAPI's /docs
# page is off: it would ask for its schema without the /api/<name> prefix.
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Who is signed in (or which API key is calling); 401 if nobody.
@app.get("/api/me")
async def me(user: CurrentUser) -> User:
    return user
