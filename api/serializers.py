# api/serializers.py

from rest_framework import serializers
from api.models import (
    Platform, Genre, ElementType, RelationType, TestCaseType,
    BugType, ConfigFieldType, Tag, Game, GameConfigField,
    Element, RelatedElement, TestCase, TestCaseTag,
    TestPlan, PlanConfigValue, PlanItem, PlanItemTC, PlanTC,
    PlanIncludes, PlanIncludeExclusion, TestRun, RunEntry,
    Attachment, Bug, AuditEntry,
)


# ── Incremental Lists ─────────────────────────────────────────────────────────

class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ['id', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class ElementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementType
        fields = ['id', 'game', 'name', 'abbreviation', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class RelationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationType
        fields = ['id', 'game', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class TestCaseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseType
        fields = ['id', 'game', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class BugTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugType
        fields = ['id', 'game', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConfigFieldTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigFieldType
        fields = ['id', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'game', 'name', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'created_at']


# ── Game Config Field ─────────────────────────────────────────────────────────

class GameConfigFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameConfigField
        fields = [
            'id', 'game', 'name', 'group_label', 'field_type',
            'default_value', 'constraints', 'order_index', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        field_type = data.get('field_type', '')
        constraints = data.get('constraints', {})
        default_value = data.get('default_value', '')
        self._validate_constraints(field_type, constraints)
        self._validate_default(field_type, constraints, default_value)
        return data

    def _validate_constraints(self, field_type, constraints):
        if field_type in ('Slider', 'Number'):
            for key in ('min', 'max'):
                if key not in constraints:
                    raise serializers.ValidationError(
                        f'{field_type} requires constraints.{key}'
                    )
        if field_type in ('Dropdown', 'Checkbox'):
            if 'options' not in constraints or not isinstance(constraints['options'], list):
                raise serializers.ValidationError(
                    f'{field_type} requires constraints.options as a list'
                )

    def _validate_default(self, field_type, constraints, default_value):
        if not default_value:
            return
        if field_type == 'Toggle':
            if default_value not in ('true', 'false'):
                raise serializers.ValidationError(
                    'Toggle default_value must be "true" or "false"'
                )
        if field_type in ('Slider', 'Number'):
            try:
                val = float(default_value)
                mn = constraints.get('min')
                mx = constraints.get('max')
                if mn is not None and val < mn:
                    raise serializers.ValidationError(
                        f'default_value {val} is below min {mn}'
                    )
                if mx is not None and val > mx:
                    raise serializers.ValidationError(
                        f'default_value {val} is above max {mx}'
                    )
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    f'{field_type} default_value must be numeric'
                )
        if field_type in ('Dropdown', 'Checkbox'):
            options = constraints.get('options', [])
            if default_value and default_value not in options:
                raise serializers.ValidationError(
                    f'default_value "{default_value}" is not in allowed options'
                )


# ── Game ──────────────────────────────────────────────────────────────────────

class GameListSerializer(serializers.ModelSerializer):
    """Lightweight — for list views and dashboards."""
    platform_name = serializers.CharField(source='platform.name', read_only=True)
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    element_count = serializers.SerializerMethodField()
    plan_count = serializers.SerializerMethodField()
    bug_count = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'code_prefix', 'platform', 'platform_name',
            'genre', 'genre_name', 'current_build_version',
            'is_deleted', 'created_by', 'created_at', 'updated_at',
            'element_count', 'plan_count', 'bug_count',
        ]
        read_only_fields = ['id', 'code_prefix', 'created_at', 'updated_at']

    def get_element_count(self, obj):
        return obj.elements.filter(is_deleted=False).count()

    def get_plan_count(self, obj):
        return obj.test_plans.filter(is_deleted=False).count()

    def get_bug_count(self, obj):
        return obj.bugs.filter(status__in=['New', 'Open', 'In Progress']).count()


class GameDetailSerializer(serializers.ModelSerializer):
    """Full detail — for game overview and settings pages."""
    platform_name = serializers.CharField(source='platform.name', read_only=True)
    genre_name = serializers.CharField(source='genre.name', read_only=True)
    config_fields = GameConfigFieldSerializer(many=True, read_only=True)
    element_types = ElementTypeSerializer(many=True, read_only=True)
    relation_types = RelationTypeSerializer(many=True, read_only=True)
    tc_types = TestCaseTypeSerializer(many=True, read_only=True)
    bug_types = BugTypeSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'code_prefix', 'platform', 'platform_name',
            'genre', 'genre_name', 'description',
            'build_versions', 'current_build_version',
            'is_deleted', 'created_by', 'created_at', 'updated_at',
            'config_fields', 'element_types', 'relation_types',
            'tc_types', 'bug_types', 'tags',
        ]
        read_only_fields = ['id', 'code_prefix', 'created_at', 'updated_at']


class GameWriteSerializer(serializers.ModelSerializer):
    """For create / update — accepts platform and genre as IDs."""
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'platform', 'genre', 'description',
            'build_versions', 'current_build_version', 'created_by',
        ]
        read_only_fields = ['id']

    def validate_current_build_version(self, value):
        # Allow empty on creation — validated properly on update
        return value

    def validate(self, data):
        build_versions = data.get('build_versions', [])
        current = data.get('current_build_version', '')
        if current and build_versions and current not in build_versions:
            raise serializers.ValidationError(
                'current_build_version must be one of the build_versions list'
            )
        return data


# ── Element ───────────────────────────────────────────────────────────────────

class RelatedElementSerializer(serializers.ModelSerializer):
    target_element_code = serializers.CharField(source='target_element.code', read_only=True)
    target_element_name = serializers.CharField(source='target_element.name', read_only=True)
    target_element_type = serializers.CharField(
        source='target_element.element_type.name', read_only=True
    )
    target_element_purpose = serializers.JSONField(
        source='target_element.purpose', read_only=True
    )
    target_element_precondition = serializers.CharField(
        source='target_element.precondition', read_only=True
    )
    relation_type_name = serializers.CharField(source='relation_type.name', read_only=True)

    class Meta:
        model = RelatedElement
        fields = [
            'id', 'element', 'target_element', 'target_element_code',
            'target_element_name', 'target_element_type',
            'target_element_purpose', 'target_element_precondition',
            'relation_type', 'relation_type_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ElementListSerializer(serializers.ModelSerializer):
    """Lightweight — for tree views and searchable dropdowns."""
    element_type_name = serializers.CharField(source='element_type.name', read_only=True)
    element_type_abr = serializers.CharField(source='element_type.abbreviation', read_only=True)
    parent_code = serializers.CharField(source='parent_element.code', read_only=True)
    parent_name = serializers.CharField(source='parent_element.name', read_only=True)
    children_count = serializers.SerializerMethodField()
    tc_count = serializers.SerializerMethodField()
    bug_count = serializers.SerializerMethodField()

    class Meta:
        model = Element
        fields = [
            'id', 'game', 'name', 'code', 'element_type', 'element_type_name',
            'element_type_abr', 'parent_element', 'parent_code', 'parent_name',
            'is_deleted', 'created_by', 'created_at', 'updated_at',
            'children_count', 'tc_count', 'bug_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']

    def get_children_count(self, obj):
        return obj.children.filter(is_deleted=False).count()

    def get_tc_count(self, obj):
        return obj.test_cases.filter(is_deleted=False).count()

    def get_bug_count(self, obj):
        return obj.bugs.count()


class ElementDetailSerializer(serializers.ModelSerializer):
    """Full detail — for element detail page."""
    element_type_name = serializers.CharField(source='element_type.name', read_only=True)
    element_type_abr = serializers.CharField(source='element_type.abbreviation', read_only=True)
    parent_element_code = serializers.CharField(source='parent_element.code', read_only=True)
    parent_element_name = serializers.CharField(source='parent_element.name', read_only=True)
    related_elements = RelatedElementSerializer(many=True, read_only=True)
    breadcrumb = serializers.SerializerMethodField()

    class Meta:
        model = Element
        fields = [
            'id', 'game', 'name', 'code',
            'element_type', 'element_type_name', 'element_type_abr',
            'purpose', 'precondition',
            'parent_element', 'parent_element_code', 'parent_element_name',
            'breadcrumb', 'related_elements',
            'is_deleted', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']

    def get_breadcrumb(self, obj):
        """Returns ordered list from root to current element."""
        crumbs = []
        current = obj
        while current:
            crumbs.append({
                'id': current.id,
                'code': current.code,
                'name': current.name,
            })
            current = current.parent_element
        return list(reversed(crumbs))


class ElementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Element
        fields = [
            'id', 'game', 'name', 'element_type', 'purpose',
            'precondition', 'parent_element', 'created_by',
        ]
        read_only_fields = ['id']

    def validate_parent_element(self, value):
        if value and self.instance and value.id == self.instance.id:
            raise serializers.ValidationError('An element cannot be its own parent.')
        return value

    def validate_purpose(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Purpose must be a list of strings.')
        return value


# ── Test Case ─────────────────────────────────────────────────────────────────

class TagMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class TestCaseListSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source='element.code', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    tc_type_name = serializers.CharField(source='tc_type.name', read_only=True)
    tags = TagMiniSerializer(many=True, read_only=True)

    class Meta:
        model = TestCase
        fields = [
            'id', 'game', 'code', 'title',
            'element', 'element_code', 'element_name',
            'plan', 'plan_code',
            'tc_type', 'tc_type_name', 'priority',
            'is_regression', 'order_index',
            'tags', 'is_deleted', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']


class TestCaseDetailSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source='element.code', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True)
    element_precondition = serializers.CharField(source='element.precondition', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    tc_type_name = serializers.CharField(source='tc_type.name', read_only=True)
    source_bug_code = serializers.CharField(source='source_bug.code', read_only=True)
    tags = TagMiniSerializer(many=True, read_only=True)

    class Meta:
        model = TestCase
        fields = [
            'id', 'game', 'code', 'title',
            'element', 'element_code', 'element_name', 'element_precondition',
            'plan', 'plan_code',
            'tc_type', 'tc_type_name', 'priority', 'precondition',
            'steps', 'expected_result',
            'is_regression', 'source_bug', 'source_bug_code',
            'order_index', 'tags',
            'is_deleted', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']


class TestCaseWriteSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(),
        source='tags', write_only=True, required=False
    )

    class Meta:
        model = TestCase
        fields = [
            'id', 'game', 'title', 'element', 'plan', 'source_bug',
            'tc_type', 'priority', 'precondition', 'steps',
            'expected_result', 'is_regression', 'order_index',
            'created_by', 'tag_ids',
        ]
        read_only_fields = ['id']

    def validate_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Steps must be a list of strings.')
        return value

    def validate(self, data):
        element = data.get('element')
        plan = data.get('plan')
        is_regression = data.get('is_regression', False)
        source_bug = data.get('source_bug')

        if is_regression and not source_bug:
            raise serializers.ValidationError(
                'Regression TCs must have a source_bug linked.'
            )
        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        tc = TestCase.objects.create(**validated_data)
        tc.tags.set(tags)
        return tc

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


# ── Plan Config Value ─────────────────────────────────────────────────────────

class PlanConfigValueSerializer(serializers.ModelSerializer):
    config_field_name = serializers.CharField(source='config_field.name', read_only=True)
    config_field_type = serializers.CharField(source='config_field.field_type', read_only=True)
    config_field_constraints = serializers.JSONField(
        source='config_field.constraints', read_only=True
    )

    class Meta:
        model = PlanConfigValue
        fields = [
            'id', 'plan', 'config_field', 'config_field_name',
            'config_field_type', 'config_field_constraints', 'value',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        config_field = data.get('config_field')
        value = data.get('value', '')
        if config_field:
            self._validate_value(config_field.field_type, config_field.constraints, value)
        return data

    def _validate_value(self, field_type, constraints, value):
        if field_type == 'Toggle':
            if value not in ('true', 'false'):
                raise serializers.ValidationError(
                    'Toggle value must be "true" or "false"'
                )
        if field_type in ('Slider', 'Number'):
            try:
                val = float(value)
                mn = constraints.get('min')
                mx = constraints.get('max')
                if mn is not None and val < mn:
                    raise serializers.ValidationError(f'Value {val} is below min {mn}')
                if mx is not None and val > mx:
                    raise serializers.ValidationError(f'Value {val} is above max {mx}')
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'{field_type} value must be numeric')
        if field_type in ('Dropdown', 'Checkbox'):
            options = constraints.get('options', [])
            if value and value not in options:
                raise serializers.ValidationError(
                    f'Value "{value}" is not in allowed options: {options}'
                )


# ── Plan Item ─────────────────────────────────────────────────────────────────

class PlanItemTCSerializer(serializers.ModelSerializer):
    tc_code = serializers.CharField(source='test_case.code', read_only=True)
    tc_title = serializers.CharField(source='test_case.title', read_only=True)
    tc_priority = serializers.CharField(source='test_case.priority', read_only=True)
    tc_type_name = serializers.CharField(source='test_case.tc_type.name', read_only=True)
    is_regression = serializers.BooleanField(source='test_case.is_regression', read_only=True)

    class Meta:
        model = PlanItemTC
        fields = [
            'id', 'plan', 'element', 'test_case',
            'tc_code', 'tc_title', 'tc_priority', 'tc_type_name',
            'is_regression', 'order_index',
        ]
        read_only_fields = ['id']


class PlanItemSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source='element.code', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True)
    element_type_name = serializers.CharField(
        source='element.element_type.name', read_only=True
    )
    tcs = serializers.SerializerMethodField()

    class Meta:
        model = PlanItem
        fields = [
            'id', 'plan', 'element', 'element_code',
            'element_name', 'element_type_name', 'order_index', 'tcs',
        ]
        read_only_fields = ['id']

    def get_tcs(self, obj):
        plan_item_tcs = PlanItemTC.objects.filter(
            plan=obj.plan, element=obj.element
        ).select_related('test_case', 'test_case__tc_type').order_by('order_index')
        return PlanItemTCSerializer(plan_item_tcs, many=True).data


class PlanTCSerializer(serializers.ModelSerializer):
    tc_code = serializers.CharField(source='test_case.code', read_only=True)
    tc_title = serializers.CharField(source='test_case.title', read_only=True)
    tc_priority = serializers.CharField(source='test_case.priority', read_only=True)

    class Meta:
        model = PlanTC
        fields = [
            'id', 'plan', 'test_case',
            'tc_code', 'tc_title', 'tc_priority', 'order_index',
        ]
        read_only_fields = ['id']


# ── Plan Includes / Exclusions ────────────────────────────────────────────────

class PlanIncludeExclusionSerializer(serializers.ModelSerializer):
    excluded_element_code = serializers.CharField(
        source='excluded_element.code', read_only=True
    )
    excluded_tc_code = serializers.CharField(
        source='excluded_tc.code', read_only=True
    )

    class Meta:
        model = PlanIncludeExclusion
        fields = [
            'id', 'inclusion', 'excluded_element', 'excluded_element_code',
            'excluded_tc', 'excluded_tc_code',
        ]
        read_only_fields = ['id']


class PlanIncludesSerializer(serializers.ModelSerializer):
    child_plan_code = serializers.CharField(source='child_plan.code', read_only=True)
    child_plan_name = serializers.CharField(source='child_plan.name', read_only=True)
    exclusions = PlanIncludeExclusionSerializer(many=True, read_only=True)

    class Meta:
        model = PlanIncludes
        fields = [
            'id', 'parent_plan', 'child_plan',
            'child_plan_code', 'child_plan_name',
            'exclusions', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ── Test Plan ─────────────────────────────────────────────────────────────────

class TestPlanListSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    tc_count = serializers.SerializerMethodField()
    element_count = serializers.SerializerMethodField()

    class Meta:
        model = TestPlan
        fields = [
            'id', 'game', 'game_name', 'name', 'short_name', 'code',
            'description', 'is_deleted', 'created_by', 'created_at', 'updated_at',
            'tc_count', 'element_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']

    def get_tc_count(self, obj):
        element_tcs = PlanItemTC.objects.filter(plan=obj).count()
        plan_tcs = PlanTC.objects.filter(plan=obj).count()
        return element_tcs + plan_tcs

    def get_element_count(self, obj):
        return obj.plan_items.count()


class TestPlanDetailSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    config_values = PlanConfigValueSerializer(many=True, read_only=True)
    plan_items = PlanItemSerializer(many=True, read_only=True)
    plan_tcs = PlanTCSerializer(many=True, read_only=True)
    included_plans = PlanIncludesSerializer(many=True, read_only=True)

    class Meta:
        model = TestPlan
        fields = [
            'id', 'game', 'game_name', 'name', 'short_name', 'code',
            'description', 'is_deleted', 'created_by', 'created_at', 'updated_at',
            'config_values', 'plan_items', 'plan_tcs', 'included_plans',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']


class TestPlanWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestPlan
        fields = [
            'id', 'game', 'name', 'short_name', 'description', 'created_by',
        ]
        read_only_fields = ['id']

    def validate_short_name(self, value):
        return value.upper().replace(' ', '')


# ── Attachment ────────────────────────────────────────────────────────────────

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            'id', 'run_entry', 'bug', 'file', 'file_name',
            'file_type', 'label', 'uploaded_at',
        ]
        read_only_fields = ['id', 'uploaded_at']

    def validate(self, data):
        run_entry = data.get('run_entry')
        bug = data.get('bug')
        if run_entry and bug:
            raise serializers.ValidationError(
                'Attachment can be linked to either a RunEntry or a Bug, not both.'
            )
        return data


# ── Run Entry ─────────────────────────────────────────────────────────────────

class RunEntrySerializer(serializers.ModelSerializer):
    tc_code = serializers.CharField(source='test_case.code', read_only=True)
    tc_title = serializers.CharField(source='test_case.title', read_only=True)
    tc_priority = serializers.CharField(source='test_case.priority', read_only=True)
    element_code = serializers.CharField(
        source='test_case.element.code', read_only=True
    )
    element_name = serializers.CharField(
        source='test_case.element.name', read_only=True
    )
    attachments = AttachmentSerializer(many=True, read_only=True)
    bugs = serializers.SerializerMethodField()
    time_taken_display = serializers.SerializerMethodField()

    class Meta:
        model = RunEntry
        fields = [
            'id', 'run', 'test_case', 'tc_code', 'tc_title', 'tc_priority',
            'element_code', 'element_name',
            'expected_result_snapshot', 'steps_snapshot',
            'element_purpose_snapshot', 'element_precondition_snapshot',
            'actual_result', 'status', 'notes',
            'time_taken_sec', 'time_taken_display',
            'opened_at', 'submitted_at',
            'added_during_run', 'created_at',
            'attachments', 'bugs',
        ]
        read_only_fields = [
            'id', 'tc_code', 'tc_title', 'tc_priority',
            'element_code', 'element_name',
            'expected_result_snapshot', 'steps_snapshot',
            'element_purpose_snapshot', 'element_precondition_snapshot',
            'time_taken_sec', 'time_taken_display',
            'created_at',
        ]

    def get_bugs(self, obj):
        return list(obj.bugs.values('id', 'code', 'summary', 'severity', 'status'))

    def get_time_taken_display(self, obj):
        if obj.time_taken_sec is None:
            return None
        h = obj.time_taken_sec // 3600
        m = (obj.time_taken_sec % 3600) // 60
        s = obj.time_taken_sec % 60
        return f'{h:02d}:{m:02d}:{s:02d}'


# ── Test Run ──────────────────────────────────────────────────────────────────

class TestRunListSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    pass_count = serializers.SerializerMethodField()
    fail_count = serializers.SerializerMethodField()
    total_count = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = TestRun
        fields = [
            'id', 'game', 'game_name', 'plan', 'plan_name', 'plan_code',
            'code', 'build_version_snapshot', 'status', 'tester_name',
            'started_at', 'ended_at', 'duration_display',
            'pass_count', 'fail_count', 'total_count',
        ]
        read_only_fields = ['id', 'code', 'started_at']

    def get_pass_count(self, obj):
        return obj.entries.filter(status='Pass', added_during_run=False).count()

    def get_fail_count(self, obj):
        return obj.entries.filter(status='Fail', added_during_run=False).count()

    def get_total_count(self, obj):
        return obj.entries.filter(added_during_run=False).count()

    def get_duration_display(self, obj):
        if not obj.ended_at or not obj.started_at:
            return None
        delta = obj.ended_at - obj.started_at
        total = int(delta.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h:02d}:{m:02d}:{s:02d}'


class TestRunDetailSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_code = serializers.CharField(source='plan.code', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    entries = RunEntrySerializer(many=True, read_only=True)
    stats = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    version_mismatch = serializers.SerializerMethodField()

    class Meta:
        model = TestRun
        fields = [
            'id', 'game', 'game_name', 'plan', 'plan_name', 'plan_code',
            'code', 'build_version_snapshot', 'game_config_snapshot',
            'tc_order_snapshot', 'status', 'tester_name',
            'started_at', 'ended_at', 'duration_display',
            'version_mismatch', 'stats', 'entries',
        ]
        read_only_fields = [
            'id', 'code', 'build_version_snapshot', 'game_config_snapshot',
            'tc_order_snapshot', 'started_at',
        ]

    def get_stats(self, obj):
        entries = obj.entries.filter(added_during_run=False)
        added = obj.entries.filter(added_during_run=True)
        bugs = obj.bugs.all()
        return {
            'total': entries.count(),
            'pass': entries.filter(status='Pass').count(),
            'fail': entries.filter(status='Fail').count(),
            'blocked': entries.filter(status='Blocked').count(),
            'skip': entries.filter(status='Skip').count(),
            'untouched': entries.filter(status='Untouched').count(),
            'bugs_from_fail': bugs.filter(is_exploratory=False).count(),
            'exploratory_bugs': bugs.filter(is_exploratory=True).count(),
            'tcs_added_regression': added.filter(
                test_case__is_regression=True
            ).count(),
            'tcs_added_missed': added.filter(
                test_case__is_regression=False
            ).count(),
        }

    def get_duration_display(self, obj):
        if not obj.ended_at or not obj.started_at:
            return None
        delta = obj.ended_at - obj.started_at
        total = int(delta.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h:02d}:{m:02d}:{s:02d}'

    def get_version_mismatch(self, obj):
        current = obj.game.current_build_version
        snapshotted = obj.build_version_snapshot
        if current and snapshotted and current != snapshotted:
            return {
                'mismatch': True,
                'run_version': snapshotted,
                'current_version': current,
            }
        return {'mismatch': False}


# ── Bug ───────────────────────────────────────────────────────────────────────

class BugListSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source='element.code', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True)
    bug_type_name = serializers.CharField(source='bug_type.name', read_only=True)
    linked_tc_count = serializers.SerializerMethodField()

    class Meta:
        model = Bug
        fields = [
            'id', 'game', 'code', 'summary',
            'element', 'element_code', 'element_name',
            'bug_type', 'bug_type_name',
            'status', 'severity', 'priority', 'reproducibility',
            'is_exploratory', 'build_version_snapshot',
            'reporter', 'created_at', 'updated_at',
            'linked_tc_codes', 'linked_tc_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at']

    def get_linked_tc_count(self, obj):
        return len(obj.linked_tc_codes) if obj.linked_tc_codes else 0


class BugDetailSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source='element.code', read_only=True)
    element_name = serializers.CharField(source='element.name', read_only=True)
    bug_type_name = serializers.CharField(source='bug_type.name', read_only=True)
    source_tc_code = serializers.CharField(source='source_tc.code', read_only=True)
    source_plan_code = serializers.CharField(source='source_plan.code', read_only=True)
    run_code = serializers.CharField(source='test_run.code', read_only=True)
    also_affects_elements = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Bug
        fields = [
            'id', 'game', 'code',
            'element', 'element_code', 'element_name',
            'run_entry', 'test_run', 'run_code',
            'source_tc', 'source_tc_code',
            'source_plan', 'source_plan_code',
            'bug_type', 'bug_type_name',
            'is_exploratory', 'build_version_snapshot',
            'summary', 'description', 'steps',
            'before_description', 'before_attachment',
            'after_description', 'after_attachment',
            'status', 'severity', 'priority', 'reproducibility',
            'also_affects', 'also_affects_elements',
            'linked_tc_codes',
            'reporter', 'created_at', 'updated_at',
            'attachments',
        ]
        read_only_fields = [
            'id', 'code', 'reporter', 'is_exploratory',
            'build_version_snapshot', 'source_tc', 'source_plan',
            'run_entry', 'test_run', 'created_at', 'updated_at',
        ]

    def get_also_affects_elements(self, obj):
        if not obj.also_affects:
            return []
        elements = Element.objects.filter(id__in=obj.also_affects).values(
            'id', 'code', 'name'
        )
        return list(elements)


class BugWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bug
        fields = [
            'id', 'game', 'element', 'bug_type',
            'summary', 'description', 'steps',
            'before_description', 'before_attachment',
            'after_description', 'after_attachment',
            'status', 'severity', 'priority', 'reproducibility',
            'also_affects',
        ]
        read_only_fields = ['id']

    def validate_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Steps must be a list of strings.')
        return value

    def validate_also_affects(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('also_affects must be a list of element IDs.')
        return value


# ── Audit Entry ───────────────────────────────────────────────────────────────

class AuditEntrySerializer(serializers.ModelSerializer):
    time_since_run_start = serializers.SerializerMethodField()

    class Meta:
        model = AuditEntry
        fields = [
            'id', 'run', 'event_type', 'timestamp',
            'time_since_run_start', 'detail', 'tester',
        ]
        read_only_fields = ['id', 'timestamp']

    def get_time_since_run_start(self, obj):
        delta = obj.timestamp - obj.run.started_at
        total = int(delta.total_seconds())
        if total < 0:
            total = 0
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f'{h:02d}:{m:02d}:{s:02d}'


# ── Global Search ─────────────────────────────────────────────────────────────

class SearchResultSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.IntegerField()
    code = serializers.CharField()
    title = serializers.CharField()
    context = serializers.CharField()
    url = serializers.CharField()
