#!/bin/sh
set -e

python <<'PYEOF'
import sys
import time

import psycopg2

from app.core.config import settings

deadline = time.time() + 60
last_error = None
while time.time() < deadline:
    try:
        conn = psycopg2.connect(settings.DATABASE_URL.replace("+psycopg2", ""))
        conn.close()
        break
    except psycopg2.OperationalError as exc:
        last_error = exc
        time.sleep(1)
else:
    print(f"Database never became reachable: {last_error}", file=sys.stderr)
    sys.exit(1)
PYEOF

alembic upgrade head

exec "$@"
