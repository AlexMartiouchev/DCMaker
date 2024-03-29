# Generated by Django 5.0.1 on 2024-03-13 20:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "populator",
            "0002_character_image_hs_character_image_iso_faction_image_and_more",
        ),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="location",
            name="party_size",
        ),
        migrations.AddField(
            model_name="location",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="locations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
