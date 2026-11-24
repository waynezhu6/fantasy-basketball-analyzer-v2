import os
from pathlib import Path

# Public URL prefixes for this app. Caddy strips /api/<name> before requests
# reach the backend, so routes are still declared under /api. Use these only
# for URLs the backend hands to the browser: redirects, links, cookie paths.
# APP is baked into the image (backend/Dockerfile); locally it's the checkout's
# folder name, matching the frontend's vite.config.ts.

#: The app's name: its repo name.
APP = (os.environ.get("APP") or Path(__file__).resolve().parents[2].name).lower()

#: e.g. /api/notes. Cookies should use this as their path.
API_BASE = f"/api/{APP}"
#: e.g. /apps/notes/
APP_BASE = f"/apps/{APP}/"
