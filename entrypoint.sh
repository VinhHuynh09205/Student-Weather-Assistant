#!/bin/sh
set -e

# Wait for database if DATABASE_URL is defined
if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database to be ready..."
  python -c "
import sys, time, urllib.parse, socket
try:
    # Safely parse DATABASE_URL
    url = urllib.parse.urlparse('$DATABASE_URL')
    host = url.hostname
    port = url.port or 5432
except Exception as e:
    print('Failed to parse DATABASE_URL:', e)
    sys.exit(1)

for _ in range(30):
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print('Database is ready!')
        sys.exit(0)
    except Exception:
        time.sleep(1)
print('Database not ready after 30 seconds, exiting.')
sys.exit(1)
"
fi

# Run migrations if RUN_MIGRATIONS env is true/set
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

# Execute the main command
exec "$@"
