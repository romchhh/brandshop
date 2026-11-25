from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0026_product_photo_import_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogSyncState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(default="idle", max_length=16)),
                ("trigger", models.CharField(blank=True, default="", max_length=16)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("rows_ok", models.PositiveIntegerField(default=0)),
                ("message", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Стан синхронізації каталогу",
                "verbose_name_plural": "Стан синхронізації каталогу",
            },
        ),
    ]
