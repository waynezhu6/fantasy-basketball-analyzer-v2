import os
import sys

import uvicorn

# `python -m app` runs the backend on PORT (3001 on the server). A deploy
# starts the new backend next to this one, then stops this one with SIGTERM:
# uvicorn stops accepting connections, finishes the requests in flight and exits.
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0" if os.environ.get("NODE_ENV") == "production" else "127.0.0.1",
        port=int(os.environ.get("PORT", "3001")),
        reload="--reload" in sys.argv,
        timeout_graceful_shutdown=25,
        access_log=False,
    )
