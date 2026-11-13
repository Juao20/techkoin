"""Run the backend test suite on a throwaway local PostgreSQL (spec 19, phase 6).

    .venv\\Scripts\\python.exe scripts\\test_postgres.py [pytest arguments]

Needs the dev extras: `pip install pgserver "psycopg[binary]"` (see docs/DEPLOYMENT.md). Without
them, point DATABASE_URL at any PostgreSQL you already have and run `pytest` from backend/.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pgserver

ROOT = Path(__file__).resolve().parent.parent


def ensure_timezone_data() -> None:
    """The pgserver wheel for Windows ships without PostgreSQL's time zone files: borrow tzdata's.

    Only needed for this throwaway test server; a real PostgreSQL install already has them.
    """
    import shutil

    target = Path(pgserver.__file__).parent / "pginstall" / "share" / "postgresql" / "timezone"
    if target.exists():
        return
    try:
        import tzdata
    except ImportError:
        return
    shutil.copytree(Path(tzdata.__file__).parent / "zoneinfo", target)


def main() -> int:
    ensure_timezone_data()
    with tempfile.TemporaryDirectory(prefix="techkoin-pg-") as data:
        server = pgserver.get_server(Path(data))
        try:
            uri = server.get_uri()
            print(f"PostgreSQL pret : {uri}")
            env = {**os.environ, "DATABASE_URL": uri}
            cmd = [sys.executable, "-m", "pytest", *(sys.argv[1:] or ["-q"])]
            return subprocess.call(cmd, cwd=ROOT / "backend", env=env)
        finally:
            server.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
