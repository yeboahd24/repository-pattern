# Generated by Django 5.1.3 on 2024-11-16 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ComparisonJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file1', models.FileField(upload_to='uploads/')),
                ('file2', models.FileField(upload_to='uploads/')),
                ('comparison_fields', models.JSONField()),
                ('status', models.CharField(default='pending', max_length=20)),
                ('result', models.JSONField(blank=True, null=True)),
            ],
        ),
    ]
