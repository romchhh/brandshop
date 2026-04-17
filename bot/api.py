import dataclasses

import requests

from dtos import CreateUser, PaginationRequest


class Api:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url

    def register_user(self, create_user: CreateUser):
        res = requests.post(
            f"{self.server_url}/registerUser",
            json=dataclasses.asdict(create_user),
        )

    def add_friend(self, user_id: int, friend_id: int):
        pass

    def search_user(self, request: PaginationRequest):
        pass

    def get_shop_statistics(self):
        base = (self.server_url or "").rstrip("/")
        if not base:
            return None
        try:
            res = requests.get(
                f"{base}/api/bot/statistics/",
                timeout=20,
            )
        except requests.RequestException:
            return None
        if res.status_code != 200:
            return None
        try:
            return res.json()
        except ValueError:
            return None

    def sync_products_from_sheets(self):
        """
        Повертає (успіх: bool, текст_для_користувача: str).
        """
        base = (self.server_url or "").rstrip("/")
        if not base:
            return (
                False,
                "Не задано SERVER_URL (або DJANGO_API_URL) — додайте в .env у корені проєкту, "
                "наприклад: SERVER_URL=http://server:8000 для Docker (ім'я сервісу в compose) або "
                "SERVER_URL=http://127.0.0.1:8000 локально. Перезапустіть бота.",
            )
        url = f"{base}/api/bot/sync-products/"
        # Не менше ніж gunicorn --timeout (за замовчуванням 3600 с — імпорт 20–30 хв + запас)
        try:
            res = requests.post(
                url,
                timeout=3600,
            )
        except requests.Timeout:
            return False, "Час очікування вичерпано (синхронізація довга). Спробуйте ще раз або перевірте сервер."
        except requests.RequestException as e:
            return False, (
                f"Помилка з'єднання: {e}\n"
                "Якщо раніше було «Remote end closed connection» — на сервері збільште "
                "gunicorn --timeout (див. server/docker-entrypoint.sh) і перезапустіть контейнер."
            )

        try:
            data = res.json()
        except ValueError:
            data = {}

        if res.status_code == 200 and data.get("ok"):
            return True, "Каталог оновлено з Google Таблиць."

        err = data.get("error") or res.text or res.reason
        return False, f"Помилка сервера ({res.status_code}): {err}"
