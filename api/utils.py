# api/utils.py

from api.models import ElementType, RelationType, TestCaseType, BugType


DEFAULT_ELEMENT_TYPES = [
    ('Interactable', 'INT'),
    ('Screen',       'SCR'),
    ('HUD Component','HUD'),
    ('Game Object',  'OBJ'),
    ('System',       'SYS'),
    ('Level / Zone', 'LVL'),
    ('Sequence',     'SEQ'),
    ('State',        'STA'),
    ('Audio',        'AUD'),
    ('Visual',       'VIS'),
    ('Logic',        'LOG'),
]

DEFAULT_RELATION_TYPES = [
    'navigates to',
    'triggers logic in',
    'affects',
    'depends on',
    'contains',
    'spawns',
    'listens to',
    'sends data to',
]

DEFAULT_TC_TYPES = [
    'Functional',
    'Visual',
    'Audio',
    'Performance',
    'Regression',
    'Smoke',
    'Edge Case',
    'Accessibility',
]

DEFAULT_BUG_TYPES = [
    'Bug',
    'Visual Glitch',
    'Audio Issue',
    'Performance',
    'Crash',
    'Data Loss',
    'Logic Error',
    'UI/UX Issue',
]


def seed_game_incremental_lists(game):
    """
    Called once when a new Game is created via GameViewSet.perform_create().
    Seeds all per-game incremental lists with defaults.
    Tester can add more or soft-delete any of these inline.
    get_or_create ensures calling this twice is safe.
    """
    for name, abr in DEFAULT_ELEMENT_TYPES:
        ElementType.objects.get_or_create(
            game=game,
            name=name,
            defaults={'abbreviation': abr},
        )

    for name in DEFAULT_RELATION_TYPES:
        RelationType.objects.get_or_create(game=game, name=name)

    for name in DEFAULT_TC_TYPES:
        TestCaseType.objects.get_or_create(game=game, name=name)

    for name in DEFAULT_BUG_TYPES:
        BugType.objects.get_or_create(game=game, name=name)
