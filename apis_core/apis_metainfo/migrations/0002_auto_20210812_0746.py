# Generated by Django 2.2.11 on 2021-08-12 07:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
        ('apis_vocabularies', '0001_initial'),
        ('apis_metainfo', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='text',
            name='kind',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='apis_vocabularies.TextType'),
        ),
        migrations.AddField(
            model_name='text',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='apis_metainfo.Source'),
        ),
        migrations.AddField(
            model_name='rootobject',
            name='self_content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='collection',
            name='collection_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='apis_vocabularies.CollectionType'),
        ),
        migrations.AddField(
            model_name='collection',
            name='groups_allowed',
            field=models.ManyToManyField(to='auth.Group'),
        ),
        migrations.AddField(
            model_name='collection',
            name='parent_class',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='apis_metainfo.Collection'),
        ),
    ]