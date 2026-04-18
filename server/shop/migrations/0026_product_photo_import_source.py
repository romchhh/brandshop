# Generated manually for incremental catalog photo import

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0025_alter_product_photo_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="photo_import_source",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="Останнє джерело фото з таблиці (нормалізоване, без повторного завантаження)",
            ),
        ),
    ]
