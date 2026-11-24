import os

from psycopg_pool import AsyncConnectionPool

# The app's Postgres, from DATABASE_URL (the server provides it when infra.yml
# has postgres: true). Use it in routes as:
#
#   async with pool.connection() as conn:
#       rows = await (await conn.execute("select ... where owner = %s", (user.id,))).fetchall()
pool = AsyncConnectionPool(os.environ.get("DATABASE_URL", ""), open=False, min_size=1, max_size=10)
