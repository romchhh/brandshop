FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Залежності окремим шаром — перезбірка коду не тягне pip знову
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

COPY . .

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
