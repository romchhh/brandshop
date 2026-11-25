"""Перевірка доступу до Google Таблиць і мапінгу колонок (без змін у БД)."""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from shop.catalog_import import (
    _is_likely_header_row,
    _normalize_article,
    get_catalog_data,
)
from shop.catalog_sheet_sources import iter_catalog_import_jobs


class Command(BaseCommand):
    help = "Читає всі блоки з таблиць і показує статистику / помилки мапінгу."

    def handle(self, *args, **options):
        jobs = list(iter_catalog_import_jobs())
        issues: list[str] = []
        articles: dict[str, list[str]] = {}
        stats: list[tuple[str, int, int]] = []

        for title, sid, fields in jobs:
            try:
                sheet = fields["sheet"]
                sheet = sheet if isinstance(sheet, list) else [sheet]
                rows = get_catalog_data(sid, sheet)
                ok = 0
                for row in rows:
                    if _is_likely_header_row(row, fields):
                        continue
                    if fields["article"] >= len(row):
                        continue
                    art = _normalize_article(row[fields["article"]])
                    if not art:
                        continue
                    ok += 1
                    articles.setdefault(art.lower(), []).append(title)
                stats.append((title, len(rows), ok))
                if ok == 0 and len(rows) > 2:
                    issues.append(f"{title}: немає артикулів у {len(rows)} рядках")
            except Exception as exc:
                issues.append(f"{title}: {exc}")

        cross = {a: cats for a, cats in articles.items() if len(set(cats)) > 1}
        self.stdout.write(f"Блоків: {len(jobs)}, унікальних артикулів: {len(articles)}")
        for title, n_rows, n_art in stats:
            self.stdout.write(f"  {title}: рядків {n_rows}, артикулів {n_art}")
        if cross:
            self.stdout.write(self.style.WARNING(f"Артикули в кількох каталогах: {len(cross)}"))
        for line in issues:
            self.stdout.write(self.style.ERROR(line))
        if not issues and not cross:
            self.stdout.write(self.style.SUCCESS("Перевірка пройдена без зауважень."))