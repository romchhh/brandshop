"""
Перевірка: скільки товарів мають заповнене поле photo в БД і чи існують файли в storage (MEDIA/product_photos).

Запуск з каталогу server:
  python manage.py check_product_photos
  python manage.py check_product_photos --limit 30
"""
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import Q

from shop.models import Product


class Command(BaseCommand):
    help = "Структура поля photo у Product та статистика / приклади шляхів у БД і на диску"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Скільки товарів з фото показати у списку перевірки файлів (default 20)",
        )

    def handle(self, *args, **options):
        limit = max(1, int(options["limit"]))
        field = Product._meta.get_field("photo")

        self.stdout.write(self.style.NOTICE("=== Product.photo (модель shop.Product) ==="))
        self.stdout.write(f"  verbose_name: {field.verbose_name}")
        self.stdout.write(f"  upload_to:    {field.upload_to}")
        self.stdout.write(f"  blank/null:   blank={field.blank}, null={field.null}")
        self.stdout.write("")

        total = Product.objects.count()
        empty_q = Q(photo__isnull=True) | Q(photo="")
        without_photo = Product.objects.filter(empty_q).count()
        with_photo = Product.objects.exclude(empty_q).count()

        self.stdout.write(self.style.NOTICE("=== Підсумок ==="))
        self.stdout.write(f"  Всього товарів:     {total}")
        self.stdout.write(f"  Записано фото в БД: {with_photo}  (photo не NULL і не порожній рядок)")
        self.stdout.write(f"  Без фото в БД:      {without_photo}")
        self.stdout.write("")

        if with_photo == 0:
            self.stdout.write(self.style.WARNING("Немає жодного товару з полем photo — перевір імпорт і MEDIA."))
            return

        self.stdout.write(self.style.NOTICE(f"=== Перші {limit} товарів з фото: шлях у БД і файл у storage ==="))
        qs = Product.objects.exclude(empty_q).order_by("pk")[:limit]
        missing = 0
        for p in qs:
            name = p.photo.name
            exists = default_storage.exists(name)
            if not exists:
                missing += 1
            status = "OK" if exists else "ВІДСУТНІЙ ФАЙЛ"
            style = self.style.SUCCESS if exists else self.style.ERROR
            self.stdout.write(
                style(
                    f"  [{status}] id={p.pk} article={p.article!r} photo.name={name!r}"
                )
            )

        self.stdout.write("")
        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"У показаних рядках файлів не знайдено у storage: {missing}. "
                    f"Перевір MEDIA_ROOT і що Django використовує той самий каталог, що й імпорт."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Усі показані записи мають файл у default storage."))
