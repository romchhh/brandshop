# Поле photo_import_source: додаємо, якщо немає; якщо вже є (NOT NULL без default) — default + DROP NOT NULL.

from django.db import migrations, models


def _ensure_column(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor == "sqlite":
        Model = apps.get_model("shop", "Product")
        table = Model._meta.db_table
        with conn.cursor() as c:
            c.execute(f'PRAGMA table_info("{table}")')
            col_names = {row[1] for row in c.fetchall()}
        if "photo_import_source" in col_names:
            return
        field = models.CharField(
            blank=True,
            default="",
            max_length=64,
            verbose_name="Джерело фото (імпорт)",
        )
        field.set_attributes_from_name("photo_import_source")
        schema_editor.add_field(Model, field)
        return
    if conn.vendor != "postgresql":
        return
    with conn.cursor() as c:
        c.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'shop_product'
              AND column_name = 'photo_import_source'
            """
        )
        if c.fetchone():
            c.execute(
                "UPDATE shop_product SET photo_import_source = '' WHERE photo_import_source IS NULL"
            )
            c.execute(
                "ALTER TABLE shop_product ALTER COLUMN photo_import_source SET DEFAULT ''"
            )
            c.execute(
                "ALTER TABLE shop_product ALTER COLUMN photo_import_source DROP NOT NULL"
            )
        else:
            c.execute(
                """ALTER TABLE shop_product ADD COLUMN photo_import_source varchar(64)
                   NOT NULL DEFAULT ''"""
            )


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0025_alter_product_photo_optional"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_ensure_column, _noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="product",
                    name="photo_import_source",
                    field=models.CharField(
                        blank=True,
                        default="",
                        max_length=64,
                        verbose_name="Джерело фото (імпорт)",
                    ),
                ),
            ],
        ),
    ]
