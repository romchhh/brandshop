from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from shop.image_optimize import optimize_file_on_disk


class Command(BaseCommand):
    help = (
        "Стиснути існуючі фото в MEDIA_ROOT (JPEG ≤1200px). "
        "Один раз на сервері: python manage.py optimize_media"
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Лише порахувати файли")

    def handle(self, *args, **options):
        root = Path(settings.MEDIA_ROOT)
        if not root.is_dir():
            self.stderr.write(f"MEDIA_ROOT не існує: {root}")
            return
        exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        changed = 0
        scanned = 0
        saved_bytes = 0
        dry = options["dry_run"]
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in exts:
                continue
            scanned += 1
            before = path.stat().st_size
            if dry:
                continue
            if optimize_file_on_disk(path):
                changed += 1
                target = path if path.exists() else path.with_suffix(".jpg")
                try:
                    after = target.stat().st_size
                    if after < before:
                        saved_bytes += before - after
                except OSError:
                    pass
        self.stdout.write(
            self.style.SUCCESS(
                f"Переглянуто: {scanned}; змінено: {changed}; "
                f"зекономлено ≈ {saved_bytes // 1024} КБ"
                + (" (dry-run)" if dry else "")
            )
        )
