# Generated by Django 3.1.14 on 2023-01-24 12:01

from django.db import migrations, models
import django.db.models.deletion

import apis_core.apis_relations.models


class Migration(migrations.Migration):

    dependencies = [
        ("apis_metainfo", "0003_auto_20220218_1530"),
        ("apis_relations", "0003_auto_20230123_1715"),
    ]

    operations = [
        migrations.AlterField(
            model_name="property",
            name="name_forward",
            field=models.CharField(
                blank=True,
                help_text='Inverse relation like: "is sub-class of" vs. "is super-class of".',
                max_length=255,
                verbose_name="Name forward",
            ),
        ),
        migrations.AlterField(
            model_name="triple",
            name="obj",
            field=apis_core.apis_relations.models.InheritanceForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="triple_set_from_obj",
                to="apis_metainfo.rootobject",
                verbose_name="Object",
            ),
        ),
        migrations.AlterField(
            model_name="triple",
            name="prop",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="triple_set_from_prop",
                to="apis_relations.property",
                verbose_name="Property",
            ),
        ),
        migrations.AlterField(
            model_name="triple",
            name="subj",
            field=apis_core.apis_relations.models.InheritanceForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="triple_set_from_subj",
                to="apis_metainfo.rootobject",
                verbose_name="Subject",
            ),
        ),
    ]
