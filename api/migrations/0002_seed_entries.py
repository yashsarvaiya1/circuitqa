# api/migrations/0002_seed_entries.py

from django.db import migrations


PLATFORMS = [
    'PC', 'Mobile', 'Console', 'Web', 'PS5', 'Xbox', 'Nintendo Switch', 'VR',
]

GENRES = [
    'Action', 'RPG', 'Puzzle', 'Strategy', 'Simulation', 'Sports',
    'Adventure', 'Horror', 'Racing', 'Platformer', 'Shooter', 'Card Game',
    'Idle', 'Casual', 'Roguelike',
]

CONFIG_FIELD_TYPES = [
    'Toggle', 'Slider', 'Input', 'Checkbox', 'Dropdown', 'Number', 'Text',
]


def seed(apps, schema_editor):
    Platform = apps.get_model('api', 'Platform')
    Genre = apps.get_model('api', 'Genre')
    ConfigFieldType = apps.get_model('api', 'ConfigFieldType')

    for name in PLATFORMS:
        Platform.objects.get_or_create(name=name)

    for name in GENRES:
        Genre.objects.get_or_create(name=name)

    for name in CONFIG_FIELD_TYPES:
        ConfigFieldType.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    Platform = apps.get_model('api', 'Platform')
    Genre = apps.get_model('api', 'Genre')
    ConfigFieldType = apps.get_model('api', 'ConfigFieldType')

    Platform.objects.filter(name__in=PLATFORMS).delete()
    Genre.objects.filter(name__in=GENRES).delete()
    ConfigFieldType.objects.filter(name__in=CONFIG_FIELD_TYPES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, reverse_code=unseed),
    ]
