# Generated manually — allow catalog import without image when Drive download fails

import shop.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0024_alter_catalog_photo_alter_catalog_photo_banner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='photo',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='product_photos/',
                validators=[shop.validators.validate_image_extension],
                verbose_name='Фото',
            ),
        ),
    ]
