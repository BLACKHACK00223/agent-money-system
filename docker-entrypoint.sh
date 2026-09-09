#!/bin/sh
set -eu

# These commands run after Coolify injects runtime environment variables,
# rather than while the Docker image is being built.
python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile -
