# Generated by Django 3.1.14 on 2022-02-01 12:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("apis_labels", "0001_initial"),
        ("apis_vocabularies", "0001_initial"),
        ("apis_entities", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="label",
            name="label_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="apis_vocabularies.labeltype",
            ),
        ),
        migrations.AddField(
            model_name="label",
            name="temp_entity",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="apis_entities.tempentityclass",
            ),
        ),
    ]
