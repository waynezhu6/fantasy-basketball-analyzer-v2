"""Schema migrations: plain SQL files in backend/migrations, applied in name
order, each once and in its own transaction. They run on startup (main.py)
before the backend takes requests.

    uv run --env-file=.env python -m app.migrate create add-notes   # new file
    uv run --env-file=.env python -m app.migrate up                 # apply by hand

There are no down migrations: undo a change with a new migration.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def migrate(url: str | None = None) -> list[str]:
    """Applies the migrations not yet run. Returns the names it applied."""
    applied = []
    with psycopg.connect(url or os.environ["DATABASE_URL"], autocommit=True) as conn:
        # One migrator at a time, should two backends ever start together.
        conn.execute("select pg_advisory_lock(hashtext('schema_migrations'))")
        conn.execute(
            "create table if not exists schema_migrations"
            " (name text primary key, run_on timestamptz not null default now())"
        )
        done = {name for (name,) in conn.execute("select name from schema_migrations")}
        for file in sorted(MIGRATIONS.glob("*.sql")):
            if file.name in done:
                continue
            with conn.transaction():
                conn.execute(file.read_text())  # type: ignore[arg-type]
                conn.execute("insert into schema_migrations (name) values (%s)", (file.name,))
            applied.append(file.name)
    return applied


def create(name: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    file = MIGRATIONS / f"{stamp}_{name}.sql"
    file.write_text(
        f"-- {name}\n"
        "-- Runs while the previous version is still serving: add tables and\n"
        "-- columns freely, but drop or rename only in a later deploy.\n\n"
    )
    return file


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["create", name]:
            print(create(name))
        case ["up"]:
            print("\n".join(migrate()) or "Nothing to migrate")
        case _:
            sys.exit("usage: python -m app.migrate create <name> | up")
