# api/models.py

from django.db import models
import json


# ── Helpers ──────────────────────────────────────────────────────────────────

def generate_prefix(name: str) -> str:
    """SuperNova Nudge → SNN, Casio Card Game → CCG"""
    words = name.strip().split()
    return ''.join(w[0].upper() for w in words if w)[:6]


# ── Incremental / Lookup Lists ────────────────────────────────────────────────

class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ElementType(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='element_types')
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('game', 'name')

    def __str__(self):
        return f'{self.name} ({self.abbreviation})'


class RelationType(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='relation_types')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('game', 'name')

    def __str__(self):
        return self.name


class TestCaseType(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='tc_types')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('game', 'name')

    def __str__(self):
        return self.name


class BugType(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='bug_types')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('game', 'name')

    def __str__(self):
        return self.name


class ConfigFieldType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Tag(models.Model):
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('game', 'name')

    def __str__(self):
        return self.name


# ── Game ──────────────────────────────────────────────────────────────────────

class Game(models.Model):
    name = models.CharField(max_length=255)
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name='games')
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name='games')
    description = models.TextField(blank=True, default='')
    code_prefix = models.CharField(max_length=10, blank=True)
    build_versions = models.JSONField(default=list)          # list of version strings, newest first
    current_build_version = models.CharField(max_length=100, blank=True, default='')
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code_prefix:
            self.code_prefix = generate_prefix(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ── Game Config Field Definitions ─────────────────────────────────────────────

class GameConfigField(models.Model):
    TYPE_TOGGLE = 'Toggle'
    TYPE_SLIDER = 'Slider'
    TYPE_INPUT = 'Input'
    TYPE_CHECKBOX = 'Checkbox'
    TYPE_DROPDOWN = 'Dropdown'
    TYPE_NUMBER = 'Number'
    TYPE_TEXT = 'Text'

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='config_fields')
    name = models.CharField(max_length=255)
    group_label = models.CharField(max_length=100, blank=True, default='')
    field_type = models.CharField(max_length=50)        # incremental — from ConfigFieldType
    default_value = models.TextField(blank=True, default='')
    constraints = models.JSONField(default=dict, blank=True)
    # constraints examples:
    #   Slider/Number: {"min": 0, "max": 100, "step": 1}
    #   Dropdown/Checkbox: {"options": ["opt1", "opt2"]}
    #   Toggle: {}   Input/Text: {}
    order_index = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order_index', 'created_at']

    def __str__(self):
        return f'{self.game.name} — {self.name}'


# ── Element ───────────────────────────────────────────────────────────────────

class Element(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='elements')
    name = models.CharField(max_length=255)
    element_type = models.ForeignKey(ElementType, on_delete=models.PROTECT, related_name='elements')
    purpose = models.JSONField(default=list)            # list of strings
    precondition = models.TextField(blank=True, default='')
    parent_element = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='children'
    )
    code = models.CharField(max_length=50, blank=True, unique=True,null=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        prefix = self.game.code_prefix
        abr = self.element_type.abbreviation
        count = Element.objects.filter(
            game=self.game,
            element_type=self.element_type
        ).count() + 1
        return f'{prefix}-{abr}-{count:03d}'

    def __str__(self):
        return f'{self.code} — {self.name}'


class RelatedElement(models.Model):
    element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='related_elements')
    target_element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='referenced_by')
    relation_type = models.ForeignKey(RelationType, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('element', 'target_element', 'relation_type')

    def __str__(self):
        return f'{self.element.code} → {self.relation_type.name} → {self.target_element.code}'


# ── Test Case ─────────────────────────────────────────────────────────────────

class TestCase(models.Model):
    PRIORITY_CRITICAL = 'Critical'
    PRIORITY_HIGH = 'High'
    PRIORITY_MEDIUM = 'Medium'
    PRIORITY_LOW = 'Low'
    PRIORITY_CHOICES = [
        (PRIORITY_CRITICAL, 'Critical'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_LOW, 'Low'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='test_cases')
    element = models.ForeignKey(
        Element, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='test_cases'
    )
    plan = models.ForeignKey(
        'TestPlan', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='scoped_test_cases'
    )
    source_bug = models.ForeignKey(
        'Bug', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_test_cases'
    )
    code = models.CharField(max_length=100, blank=True, unique=True,null=True)
    title = models.CharField(max_length=500)
    tc_type = models.ForeignKey(
        TestCaseType, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='test_cases'
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    precondition = models.TextField(blank=True, default='')
    steps = models.JSONField(default=list)              # ordered list of strings
    expected_result = models.TextField()
    tags = models.ManyToManyField(Tag, through='TestCaseTag', blank=True)
    is_regression = models.BooleanField(default=False)
    order_index = models.PositiveIntegerField(default=0)  # global order within element
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order_index', 'created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        prefix = self.game.code_prefix

        if self.is_regression:
            # Will be set after base code is known — handled in viewset
            return f'TC-TEMP-{self.game.id}-{TestCase.objects.filter(game=self.game).count()+1}'

        if self.element and not self.plan:
            # A) Element-only
            seq = TestCase.objects.filter(game=self.game, element=self.element, plan__isnull=True).count() + 1
            return f'TC-{self.element.code}-{seq:02d}'

        if self.element and self.plan:
            # B) Element + Plan
            plan_short = self.plan.short_name.upper() if self.plan.short_name else f'PLAN{self.plan.id}'
            seq = TestCase.objects.filter(game=self.game, element=self.element, plan=self.plan).count() + 1
            return f'TC-{plan_short}-{self.element.code}-{seq:02d}'

        if self.plan and not self.element:
            # C) Plan-only
            plan_short = self.plan.short_name.upper() if self.plan.short_name else f'PLAN{self.plan.id}'
            seq = TestCase.objects.filter(game=self.game, element__isnull=True, plan=self.plan).count() + 1
            return f'TC-{plan_short}-{seq:03d}'

        # Fallback
        seq = TestCase.objects.filter(game=self.game).count() + 1
        return f'TC-{prefix}-{seq:03d}'

    def __str__(self):
        return f'{self.code} — {self.title}'


class TestCaseTag(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('test_case', 'tag')


# ── Test Plan ─────────────────────────────────────────────────────────────────

class TestPlan(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='test_plans')
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=30, blank=True, default='')
    description = models.TextField(blank=True, default='')
    code = models.CharField(max_length=100, blank=True, unique=True,null=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = self.game.code_prefix
            seq = TestPlan.objects.filter(game=self.game).count() + 1
            short = self.short_name.upper() if self.short_name else 'PLAN'
            self.code = f'PLAN-{prefix}-{seq:03d}-{short}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} — {self.name}'


class PlanConfigValue(models.Model):
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='config_values')
    config_field = models.ForeignKey(GameConfigField, on_delete=models.CASCADE, related_name='plan_values')
    value = models.TextField()

    class Meta:
        unique_together = ('plan', 'config_field')

    def __str__(self):
        return f'{self.plan.code} — {self.config_field.name} = {self.value}'


class PlanItem(models.Model):
    """An element included in a test plan."""
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='plan_items')
    element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='plan_items')
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('plan', 'element')
        ordering = ['order_index']

    def __str__(self):
        return f'{self.plan.code} / {self.element.code}'


class PlanItemTC(models.Model):
    """A TC included under a specific element in a specific plan."""
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='plan_item_tcs')
    element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='plan_item_tcs')
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='plan_item_tcs')
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('plan', 'element', 'test_case')
        ordering = ['order_index']

    def __str__(self):
        return f'{self.plan.code} / {self.element.code} / {self.test_case.code}'


class PlanTC(models.Model):
    """Plan-only TC (no element) included in a plan."""
    plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='plan_tcs')
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='plan_tcs')
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('plan', 'test_case')
        ordering = ['order_index']


class PlanIncludes(models.Model):
    """Parent plan includes a child plan (live sync)."""
    parent_plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='included_plans')
    child_plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='included_in_plans')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parent_plan', 'child_plan')

    def __str__(self):
        return f'{self.parent_plan.code} includes {self.child_plan.code}'


class PlanIncludeExclusion(models.Model):
    """Elements or TCs excluded from an included plan."""
    inclusion = models.ForeignKey(PlanIncludes, on_delete=models.CASCADE, related_name='exclusions')
    excluded_element = models.ForeignKey(
        Element, null=True, blank=True,
        on_delete=models.CASCADE, related_name='plan_exclusions'
    )
    excluded_tc = models.ForeignKey(
        TestCase, null=True, blank=True,
        on_delete=models.CASCADE, related_name='plan_exclusions'
    )

    def __str__(self):
        return f'Exclusion in {self.inclusion}'


# ── Test Run ──────────────────────────────────────────────────────────────────

class TestRun(models.Model):
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETE = 'Complete'
    STATUS_ABANDONED = 'Abandoned'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_ABANDONED, 'Abandoned'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='test_runs')
    plan = models.ForeignKey(TestPlan, on_delete=models.PROTECT, related_name='test_runs')
    code = models.CharField(max_length=200, blank=True, unique=True,null=True)
    build_version_snapshot = models.CharField(max_length=100)
    game_config_snapshot = models.JSONField(default=dict)   # full config at run start
    tc_order_snapshot = models.JSONField(default=list)       # resolved ordered TC id list
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    tester_name = models.CharField(max_length=150)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            plan_code = self.plan.code if self.plan_id else 'PLAN'
            version = self.build_version_snapshot.replace(' ', '')
            seq = TestRun.objects.filter(game=self.game, plan=self.plan).count() + 1
            self.code = f'RUN-{plan_code}-{version}-{seq:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class RunEntry(models.Model):
    STATUS_UNTOUCHED = 'Untouched'
    STATUS_PASS = 'Pass'
    STATUS_FAIL = 'Fail'
    STATUS_BLOCKED = 'Blocked'
    STATUS_SKIP = 'Skip'
    STATUS_CHOICES = [
        (STATUS_UNTOUCHED, 'Untouched'),
        (STATUS_PASS, 'Pass'),
        (STATUS_FAIL, 'Fail'),
        (STATUS_BLOCKED, 'Blocked'),
        (STATUS_SKIP, 'Skip'),
    ]

    run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='entries')
    test_case = models.ForeignKey(TestCase, on_delete=models.PROTECT, related_name='run_entries')

    # Snapshots at run start
    expected_result_snapshot = models.TextField(blank=True, default='')
    steps_snapshot = models.JSONField(default=list)
    element_purpose_snapshot = models.JSONField(default=list)
    element_precondition_snapshot = models.TextField(blank=True, default='')

    # Tester input
    actual_result = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UNTOUCHED)
    notes = models.TextField(blank=True, default='')
    time_taken_sec = models.PositiveIntegerField(null=True, blank=True)

    opened_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Is this TC added during the run (not in original snapshot)?
    added_during_run = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.run.code} / {self.test_case.code} — {self.status}'


# ── Attachment ────────────────────────────────────────────────────────────────

class Attachment(models.Model):
    run_entry = models.ForeignKey(
        RunEntry, null=True, blank=True,
        on_delete=models.CASCADE, related_name='attachments'
    )
    bug = models.ForeignKey(
        'Bug', null=True, blank=True,
        on_delete=models.CASCADE, related_name='attachments'
    )
    file = models.FileField(upload_to='attachments/')
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=100)
    label = models.CharField(max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name


# ── Bug ───────────────────────────────────────────────────────────────────────

class Bug(models.Model):
    STATUS_NEW = 'New'
    STATUS_OPEN = 'Open'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_FIXED = 'Fixed'
    STATUS_VERIFIED = 'Verified'
    STATUS_CLOSED = 'Closed'
    STATUS_WONT_FIX = "Won't Fix"
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_FIXED, 'Fixed'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_WONT_FIX, "Won't Fix"),
    ]

    SEVERITY_CRITICAL = 'Critical'
    SEVERITY_HIGH = 'High'
    SEVERITY_MEDIUM = 'Medium'
    SEVERITY_LOW = 'Low'
    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, 'Critical'),
        (SEVERITY_HIGH, 'High'),
        (SEVERITY_MEDIUM, 'Medium'),
        (SEVERITY_LOW, 'Low'),
    ]

    REPRO_ALWAYS = 'Always'
    REPRO_SOMETIMES = 'Sometimes'
    REPRO_RARELY = 'Rarely'
    REPRO_ONCE = 'Once'
    REPRO_CANNOT = 'Cannot Reproduce'
    REPRO_CHOICES = [
        (REPRO_ALWAYS, 'Always'),
        (REPRO_SOMETIMES, 'Sometimes'),
        (REPRO_RARELY, 'Rarely'),
        (REPRO_ONCE, 'Once'),
        (REPRO_CANNOT, 'Cannot Reproduce'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='bugs')
    element = models.ForeignKey(
        Element, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bugs'
    )
    run_entry = models.ForeignKey(
        RunEntry, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bugs'
    )
    test_run = models.ForeignKey(
        TestRun, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bugs'
    )
    source_tc = models.ForeignKey(
        TestCase, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sourced_bugs'
    )
    source_plan = models.ForeignKey(
        TestPlan, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sourced_bugs'
    )
    bug_type = models.ForeignKey(
        BugType, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bugs'
    )

    code = models.CharField(max_length=100, blank=True, unique=True,null=True)
    is_exploratory = models.BooleanField(default=False)
    build_version_snapshot = models.CharField(max_length=100, blank=True, default='')

    summary = models.CharField(max_length=500)
    description = models.TextField()
    steps = models.JSONField(default=list)              # ordered list of strings

    before_description = models.TextField(blank=True, default='')
    before_attachment = models.ForeignKey(
        Attachment, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bug_before'
    )
    after_description = models.TextField(blank=True, default='')
    after_attachment = models.ForeignKey(
        Attachment, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='bug_after'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default=SEVERITY_MEDIUM)
    priority = models.CharField(max_length=20, choices=[
        ('Critical', 'Critical'), ('High', 'High'),
        ('Medium', 'Medium'), ('Low', 'Low'),
    ], default='Medium')
    reproducibility = models.CharField(max_length=30, choices=REPRO_CHOICES, default=REPRO_ALWAYS)

    also_affects = models.JSONField(default=list)       # list of element IDs
    linked_tc_codes = models.JSONField(default=list)    # grows as TCs are created from this bug

    reporter = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        prefix = self.game.code_prefix
        if not self.is_exploratory and self.element:
            seq = Bug.objects.filter(game=self.game, is_exploratory=False, element__isnull=False).count() + 1
            return f'BUG-{self.element.code}-{seq:03d}'
        else:
            seq = Bug.objects.filter(game=self.game, is_exploratory=True).count() + \
                  Bug.objects.filter(game=self.game, element__isnull=True).count() + 1
            return f'EXPL-{prefix}-{seq:03d}'

    def __str__(self):
        return f'{self.code} — {self.summary}'


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditEntry(models.Model):
    EVENT_RUN_STARTED = 'Run Started'
    EVENT_TC_OPENED = 'TC Opened'
    EVENT_TC_RESULT = 'TC Result Submitted'
    EVENT_BUG_FILED = 'Bug Filed'
    EVENT_TC_CREATED = 'TC Created During Run'
    EVENT_TC_LINKED = 'TC Linked to Bug'
    EVENT_RUN_COMPLETED = 'Run Completed'
    EVENT_RUN_ABANDONED = 'Run Abandoned'
    EVENT_CHOICES = [
        (EVENT_RUN_STARTED, 'Run Started'),
        (EVENT_TC_OPENED, 'TC Opened'),
        (EVENT_TC_RESULT, 'TC Result Submitted'),
        (EVENT_BUG_FILED, 'Bug Filed'),
        (EVENT_TC_CREATED, 'TC Created During Run'),
        (EVENT_TC_LINKED, 'TC Linked to Bug'),
        (EVENT_RUN_COMPLETED, 'Run Completed'),
        (EVENT_RUN_ABANDONED, 'Run Abandoned'),
    ]

    run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='audit_entries')
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    detail = models.JSONField(default=dict)
    tester = models.CharField(max_length=150)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.run.code} — {self.event_type} @ {self.timestamp}'
