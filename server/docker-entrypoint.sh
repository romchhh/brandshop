#!/bin/sh
set -e
until cd /app
do
    echo "Wait for server volume..."
done

echo "Applying database migrations..."
until python manage.py migrate --noinput
do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "Database migrations OK."

python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','server.settings'); import django; django.setup(); from shop.beat_setup import ensure_catalog_sync_periodic_tasks; ensure_catalog_sync_periodic_tasks()" || true

# Статика для адмінки (Whitenoise) — тихо, якщо вже зібрано
python manage.py collectstatic --noinput 2>/dev/null || true

# Економія RAM: 1 gunicorn worker + 1 celery process (синк рідко)
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-3600}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
GUNICORN_THREADS="${GUNICORN_THREADS:-2}"
CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-1}"

# Один процес: worker + beat. Окремий beat раніше «планував» задачу,
# а worker часто вже не жив — імпорт не виконувався.
start_celery() {
    celery -A server worker \
        --beat \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler \
        --loglevel="${CELERY_LOGLEVEL:-warning}" \
        --queues=default \
        --concurrency="$CELERY_CONCURRENCY" \
        --prefetch-multiplier=1 \
        --max-tasks-per-child=8 \
        --without-gossip --without-mingle --without-heartbeat &
    echo $!
}

gunicorn server.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$GUNICORN_WORKERS" \
    --threads "$GUNICORN_THREADS" \
    --timeout "$GUNICORN_TIMEOUT" \
    --graceful-timeout 60 \
    --max-requests 500 \
    --max-requests-jitter 50 &
GUNICORN_PID=$!

CELERY_PID=$(start_celery)

echo "Gunicorn pid=$GUNICORN_PID (workers=$GUNICORN_WORKERS threads=$GUNICORN_THREADS), Celery worker+beat=$CELERY_PID"

while kill -0 "$GUNICORN_PID" 2>/dev/null; do
    sleep 30
    if ! kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "Celery worker+beat exited — restarting…"
        CELERY_PID=$(start_celery)
    fi
done

wait "$GUNICORN_PID"
