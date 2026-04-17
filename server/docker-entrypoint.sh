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

# Розклад Celery beat у БД (django-celery-beat) — після міграцій, без запитів у AppConfig.ready()
python manage.py shell -c "from shop.beat_setup import ensure_catalog_sync_periodic_tasks; ensure_catalog_sync_periodic_tasks()" || true

# Запускаємо gunicorn, celery worker і celery beat у фоновому режимі
# GUNICORN_TIMEOUT: інакше 30 с за замовчуванням — довгий імпорт обриває з'єднання (RemoteDisconnected).
# За замовчуванням 3600 с (60 хв): імпорт з таблиць часто 20–30 хв, потрібен запас.
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-3600}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"
# Кілька воркерів: довгий запит не блокує весь інший трафік (errno 107 часто від обрізаних клієнтів — не критично).
gunicorn server.wsgi:application --bind 0.0.0.0:8000 --workers "$GUNICORN_WORKERS" --timeout "$GUNICORN_TIMEOUT" --graceful-timeout 60 &
celery -A server worker --loglevel=info --queues=default &
celery -A server beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# Залишаємо контейнер працюючим
wait