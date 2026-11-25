from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0027_catalogsyncstate"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogsyncstate",
            name="progress_done",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="catalogsyncstate",
            name="progress_total",
            field=models.PositiveIntegerField(default=1000),
        ),
    ]
