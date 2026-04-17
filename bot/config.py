import os
from pathlib import Path


def _load_dotenv() -> None:
    """Підхоплює .env з кореня репозиторію (give-me-project/.env), якщо є python-dotenv."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env", override=False)
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


_load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
SITE_URL = os.getenv("SITE_URL")
# Базовий URL Django API (без /api/ в кінці). У Docker: http://server:8000 (ім'я сервісу; не django_server — підкреслення в Host некоректні для Django).
SERVER_URL = (
    os.getenv("SERVER_URL") or os.getenv("DJANGO_API_URL") or ""
).strip().rstrip("/")
ADMIN_ID = os.getenv("ADMIN_ID")


def _parse_admin_ids() -> list:
    raw = os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID") or ""
    if not raw:
        return []
    out = []
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


ADMIN_IDS = _parse_admin_ids()