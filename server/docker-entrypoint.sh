#!/bin/sh
set -e
until cd /app
do
    echo "Wait for server volume..."
done

# Ініціалізація схеми БД: чекаємо на PostgreSQL і застосовуємо міграції Django
echo "Applying database migrations..."
until python manage.py migrate --noinput
do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "Database migrations OK."

# Розклад Celery beat у БД (django-celery-beat) — після міграцій.
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','server.settings'); import django; django.setup(); from shop.beat_setup import ensure_catalog_sync_periodic_tasks; ensure_catalog_sync_periodic_tasks()" || true

GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-3600}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"

start_celery_worker() {
    celery -A server worker --loglevel=info --queues=default &
    echo $!
}

start_celery_beat() {
    celery -A server beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &
    echo $!
}

gunicorn server.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$GUNICORN_WORKERS" \
    --timeout "$GUNICORN_TIMEOUT" \
    --graceful-timeout 60 &
GUNICORN_PID=$!

CELERY_WORKER_PID=$(start_celery_worker)
CELERY_BEAT_PID=$(start_celery_beat)

echo "Gunicorn pid=$GUNICORN_PID, Celery worker pid=$CELERY_WORKER_PID, Celery beat pid=$CELERY_BEAT_PID"

# Раніше `wait` без аргументів чекав усі фонові процеси: якщо падав worker/beat,
# скрипт завершувався і контейнер зупинявся — розклад у БД є, але задачі не виконуються.
while kill -0 "$GUNICORN_PID" 2>/dev/null; do
    sleep 20
    if ! kill -0 "$CELERY_WORKER_PID" 2>/dev/null; then
        echo "Celery worker exited — restarting…"
        CELERY_WORKER_PID=$(start_celery_worker)
        echo "Celery worker restarted pid=$CELERY_WORKER_PID"
    fi
    if ! kill -0 "$CELERY_BEAT_PID" 2>/dev/null; then
        echo "Celery beat exited — restarting…"
        CELERY_BEAT_PID=$(start_celery_beat)
        echo "Celery beat restarted pid=$CELERY_BEAT_PID"
    fi
done

wait "$GUNICORN_PID"
