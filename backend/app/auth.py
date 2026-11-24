import os
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from .paths import APP

# Who is signed in, from the shared passkey sign-in service
# (github.com/waynezhu6/auth). Its session cookie is sent to every app on the
# domain; this backend passes it on to the service over the server's internal
# network, which answers with the user or 401.
#
# Callers that can't sign in (scripts, other servers) send an API key instead,
# as "Authorization: Bearer wz_<app>_...", made on the auth service's admin
# page for this app. It's passed on the same way, with this app's name, and
# the service answers with the key's owner only if the key is for this app.
#
# Locally there's no auth service: set AUTH_DEV_USER in backend/.env to be
# signed in as that name, or leave it unset to be signed out. The server sets
# NODE_ENV=production for every app, whatever its language.
AUTH_URL = os.environ.get("AUTH_URL", "http://auth-backend:3001")
DEV_USER = None if os.environ.get("NODE_ENV") == "production" else os.environ.get("AUTH_DEV_USER")

client = httpx.AsyncClient(timeout=5)


class User(BaseModel):
    #: Stable for the account's lifetime. Key your data on this.
    id: str
    name: str
    #: Set when the caller used an API key rather than signing in: the key's name.
    key: str | None = None


async def current_user(request: Request) -> User | None:
    """The signed-in user, or None. Answers 503 if the auth service can't be reached."""
    if DEV_USER:
        return User(id=f"dev-{DEV_USER}", name=DEV_USER)
    authorization = request.headers.get("authorization")
    cookie = request.headers.get("cookie")
    # A request with a key is judged on the key alone.
    headers = {"authorization": authorization} if authorization else {"cookie": cookie} if cookie else None
    if headers is None:
        return None
    try:
        res = await client.get(f"{AUTH_URL}/api/verify", params={"app": APP}, headers=headers)
    except httpx.HTTPError as err:
        print(f"Couldn't check sign-in: {err!r}", flush=True)
        raise HTTPException(503, "Sign-in is unavailable right now")
    if res.status_code == 401:
        return None
    if res.is_error:
        print(f"Couldn't check sign-in: auth service answered {res.status_code}", flush=True)
        raise HTTPException(503, "Sign-in is unavailable right now")
    return User.model_validate(res.json())


async def require_user(user: Annotated[User | None, Depends(current_user)]) -> User:
    """For routes that need a signed-in user, or answers 401. The frontend
    sends the browser to loginUrl() (api.ts) on a 401.

        @app.get("/api/notes")
        async def notes(user: CurrentUser): ...  # user.id
    """
    if user is None:
        raise HTTPException(401, "Sign in first")
    return user


#: A route parameter typed CurrentUser gets the signed-in user, or the route answers 401.
CurrentUser = Annotated[User, Depends(require_user)]
#: A route parameter typed MaybeUser gets the signed-in user or None.
MaybeUser = Annotated[User | None, Depends(current_user)]
