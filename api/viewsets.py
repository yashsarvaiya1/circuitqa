# api/viewsets.py

from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models import (
    Platform, Genre, ElementType, RelationType, TestCaseType,
    BugType, ConfigFieldType, Tag, Game, GameConfigField,
    Element, RelatedElement, TestCase, TestCaseTag,
    TestPlan, PlanConfigValue, PlanItem, PlanItemTC, PlanTC,
    PlanIncludes, PlanIncludeExclusion, TestRun, RunEntry,
    Attachment, Bug, AuditEntry,
)
from api.serializers import (
    PlatformSerializer, GenreSerializer, ElementTypeSerializer,
    RelationTypeSerializer, TestCaseTypeSerializer, BugTypeSerializer,
    ConfigFieldTypeSerializer, TagSerializer,
    GameListSerializer, GameDetailSerializer, GameWriteSerializer,
    GameConfigFieldSerializer,
    ElementListSerializer, ElementDetailSerializer, ElementWriteSerializer,
    RelatedElementSerializer,
    TestCaseListSerializer, TestCaseDetailSerializer, TestCaseWriteSerializer,
    TestPlanListSerializer, TestPlanDetailSerializer, TestPlanWriteSerializer,
    PlanConfigValueSerializer, PlanItemSerializer, PlanItemTCSerializer,
    PlanTCSerializer, PlanIncludesSerializer, PlanIncludeExclusionSerializer,
    TestRunListSerializer, TestRunDetailSerializer,
    RunEntrySerializer, AttachmentSerializer,
    BugListSerializer, BugDetailSerializer, BugWriteSerializer,
    AuditEntrySerializer, SearchResultSerializer,
)
from api.utils import seed_game_incremental_lists


# ── Helpers ───────────────────────────────────────────────────────────────────

def audit(run, event_type, detail, tester):
    AuditEntry.objects.create(
        run=run,
        event_type=event_type,
        detail=detail,
        tester=tester,
    )


def resolve_plan_tcs(plan, excluded_element_ids=None, excluded_tc_ids=None):
    """
    Resolves the full ordered TC list for a plan including live-synced
    included plans. Returns list of dicts with tc_id, element_id, order info.
    Excluded element/tc IDs apply only when called from an inclusion context.
    """
    excluded_element_ids = excluded_element_ids or []
    excluded_tc_ids = excluded_tc_ids or []
    result = []

    # Element-scoped TCs from this plan
    plan_items = PlanItem.objects.filter(plan=plan).order_by('order_index')
    for pi in plan_items:
        if pi.element_id in excluded_element_ids:
            continue
        plan_item_tcs = PlanItemTC.objects.filter(
            plan=plan, element=pi.element
        ).order_by('order_index')
        for pitc in plan_item_tcs:
            if pitc.test_case_id in excluded_tc_ids:
                continue
            result.append({
                'tc_id': pitc.test_case_id,
                'element_id': pi.element_id,
                'plan_id': plan.id,
                'order_index': pitc.order_index,
                'is_plan_only': False,
            })

    # Plan-only TCs
    plan_tcs = PlanTC.objects.filter(plan=plan).order_by('order_index')
    for ptc in plan_tcs:
        if ptc.test_case_id in excluded_tc_ids:
            continue
        result.append({
            'tc_id': ptc.test_case_id,
            'element_id': None,
            'plan_id': plan.id,
            'order_index': ptc.order_index,
            'is_plan_only': True,
        })

    # Live-synced included plans
    inclusions = PlanIncludes.objects.filter(parent_plan=plan).select_related('child_plan')
    for inclusion in inclusions:
        excl_elements = list(
            inclusion.exclusions.filter(excluded_element__isnull=False)
            .values_list('excluded_element_id', flat=True)
        )
        excl_tcs = list(
            inclusion.exclusions.filter(excluded_tc__isnull=False)
            .values_list('excluded_tc_id', flat=True)
        )
        child_tcs = resolve_plan_tcs(inclusion.child_plan, excl_elements, excl_tcs)
        result.extend(child_tcs)

    return result


def build_config_snapshot(plan):
    """
    Returns dict of {field_name: value} using plan-scoped values
    or game defaults where plan hasn't set a value.
    """
    snapshot = {}
    config_fields = GameConfigField.objects.filter(game=plan.game)
    plan_values = {
        pv.config_field_id: pv.value
        for pv in PlanConfigValue.objects.filter(plan=plan)
    }
    for field in config_fields:
        value = plan_values.get(field.id, field.default_value)
        snapshot[field.name] = {
            'value': value,
            'type': field.field_type,
            'group_label': field.group_label,
        }
    return snapshot


# ── Incremental List ViewSets ─────────────────────────────────────────────────

class PlatformViewSet(viewsets.ModelViewSet):
    serializer_class = PlatformSerializer

    def get_queryset(self):
        return Platform.objects.all().order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GenreViewSet(viewsets.ModelViewSet):
    serializer_class = GenreSerializer

    def get_queryset(self):
        return Genre.objects.all().order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ElementTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ElementTypeSerializer

    def get_queryset(self):
        qs = ElementType.objects.all()
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RelationTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RelationTypeSerializer

    def get_queryset(self):
        qs = RelationType.objects.all()
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestCaseTypeViewSet(viewsets.ModelViewSet):
    serializer_class = TestCaseTypeSerializer

    def get_queryset(self):
        qs = TestCaseType.objects.all()
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BugTypeViewSet(viewsets.ModelViewSet):
    serializer_class = BugTypeSerializer

    def get_queryset(self):
        qs = BugType.objects.all()
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfigFieldTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ConfigFieldTypeSerializer

    def get_queryset(self):
        return ConfigFieldType.objects.all().order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        qs = Tag.objects.filter(is_deleted=False)
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('name')

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_deleted = True
        obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Game ViewSet ──────────────────────────────────────────────────────────────

class GameViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = Game.objects.filter(is_deleted=False).select_related('platform', 'genre')

        # Filters
        platform = self.request.query_params.get('platform')
        genre = self.request.query_params.get('genre')
        created_by = self.request.query_params.get('created_by')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        search = self.request.query_params.get('search')

        if platform:
            qs = qs.filter(platform_id=platform)
        if genre:
            qs = qs.filter(genre_id=genre)
        if created_by:
            qs = qs.filter(created_by__icontains=created_by)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return GameListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return GameWriteSerializer
        return GameDetailSerializer

    def perform_create(self, serializer):
        game = serializer.save()
        seed_game_incremental_lists(game)

    def destroy(self, request, *args, **kwargs):
        game = self.get_object()
        game.is_deleted = True
        game.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='versions/add')
    def add_version(self, request, pk=None):
        """Add a new build version to the game's version list."""
        game = self.get_object()
        version = request.data.get('version', '').strip()
        if not version:
            return Response(
                {'error': 'version is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        versions = game.build_versions or []
        if version in versions:
            return Response(
                {'error': 'Version already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Newest at top
        versions.insert(0, version)
        game.build_versions = versions
        game.current_build_version = version
        game.save()
        return Response({'build_versions': game.build_versions,
                         'current_build_version': game.current_build_version})

    @action(detail=True, methods=['post'], url_path='versions/set-current')
    def set_current_version(self, request, pk=None):
        """Set the active build version."""
        game = self.get_object()
        version = request.data.get('version', '').strip()
        if version not in (game.build_versions or []):
            return Response(
                {'error': 'Version not in list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        game.current_build_version = version
        game.save()
        return Response({'current_build_version': game.current_build_version})

    @action(detail=True, methods=['delete'], url_path='versions/remove')
    def remove_version(self, request, pk=None):
        """Remove a build version from the list."""
        game = self.get_object()
        version = request.data.get('version', '').strip()
        versions = game.build_versions or []
        if version not in versions:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        versions.remove(version)
        game.build_versions = versions
        if game.current_build_version == version:
            game.current_build_version = versions[0] if versions else ''
        game.save()
        return Response({'build_versions': game.build_versions,
                         'current_build_version': game.current_build_version})

    @action(detail=True, methods=['get'], url_path='runs-by-version')
    def runs_by_version(self, request, pk=None):
        """Returns test runs grouped by build version for game overview."""
        game = self.get_object()
        runs = TestRun.objects.filter(game=game).order_by(
            '-build_version_snapshot', '-started_at'
        )
        grouped = {}
        for run in runs:
            v = run.build_version_snapshot
            if v not in grouped:
                grouped[v] = []
            grouped[v].append(TestRunListSerializer(run).data)
        return Response(grouped)


# ── Game Config Field ViewSet ─────────────────────────────────────────────────

class GameConfigFieldViewSet(viewsets.ModelViewSet):
    serializer_class = GameConfigFieldSerializer

    def get_queryset(self):
        qs = GameConfigField.objects.all()
        game_id = self.request.query_params.get('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        return qs.order_by('order_index', 'created_at')

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Accepts: [{"id": 1, "order_index": 0}, ...]
        Updates order_index for each config field.
        """
        items = request.data.get('items', [])
        for item in items:
            GameConfigField.objects.filter(id=item['id']).update(
                order_index=item['order_index']
            )
        return Response({'status': 'reordered'})


# ── Element ViewSet ───────────────────────────────────────────────────────────

class ElementViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = Element.objects.filter(is_deleted=False).select_related(
            'element_type', 'parent_element', 'game'
        )
        game_id = self.request.query_params.get('game')
        element_type = self.request.query_params.get('element_type')
        created_by = self.request.query_params.get('created_by')
        has_parent = self.request.query_params.get('has_parent')
        parent = self.request.query_params.get('parent')
        search = self.request.query_params.get('search')

        if game_id:
            qs = qs.filter(game_id=game_id)
        if element_type:
            qs = qs.filter(element_type_id=element_type)
        if created_by:
            qs = qs.filter(created_by__icontains=created_by)
        if has_parent == 'true':
            qs = qs.filter(parent_element__isnull=False)
        if has_parent == 'false':
            qs = qs.filter(parent_element__isnull=True)
        if parent:
            qs = qs.filter(parent_element_id=parent)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

        return qs.order_by('created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ElementWriteSerializer
        if self.action == 'retrieve':
            return ElementDetailSerializer
        return ElementListSerializer

    def destroy(self, request, *args, **kwargs):
        element = self.get_object()
        element.is_deleted = True
        element.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        """
        Returns full element tree for a game — root elements with
        children nested recursively.
        """
        game_id = request.query_params.get('game')
        if not game_id:
            return Response({'error': 'game param required'},
                            status=status.HTTP_400_BAD_REQUEST)

        all_elements = Element.objects.filter(
            game_id=game_id, is_deleted=False
        ).select_related('element_type', 'parent_element').order_by('created_at')

        def build_node(el):
            data = ElementListSerializer(el).data
            data['children'] = [
                build_node(child)
                for child in all_elements
                if child.parent_element_id == el.id
            ]
            return data

        roots = [el for el in all_elements if el.parent_element_id is None]
        return Response([build_node(r) for r in roots])

    @action(detail=False, methods=['get'], url_path='search-dropdown')
    def search_dropdown(self, request):
        """
        Lightweight search for searchable dropdowns — returns id, code, name only.
        Handles 1000+ elements efficiently.
        """
        game_id = request.query_params.get('game')
        q = request.query_params.get('q', '')
        qs = Element.objects.filter(is_deleted=False)
        if game_id:
            qs = qs.filter(game_id=game_id)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        return Response(
            list(qs.values('id', 'code', 'name', 'element_type__name')[:100])
        )


# ── Related Element ViewSet ───────────────────────────────────────────────────

class RelatedElementViewSet(viewsets.ModelViewSet):
    serializer_class = RelatedElementSerializer

    def get_queryset(self):
        qs = RelatedElement.objects.select_related(
            'target_element', 'target_element__element_type', 'relation_type'
        )
        element_id = self.request.query_params.get('element')
        if element_id:
            qs = qs.filter(element_id=element_id)
        return qs


# ── Test Case ViewSet ─────────────────────────────────────────────────────────

class TestCaseViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = TestCase.objects.filter(is_deleted=False).select_related(
            'element', 'plan', 'tc_type', 'source_bug', 'game'
        )
        game_id = self.request.query_params.get('game')
        element_id = self.request.query_params.get('element')
        plan_id = self.request.query_params.get('plan')
        tc_type = self.request.query_params.get('tc_type')
        priority = self.request.query_params.get('priority')
        is_regression = self.request.query_params.get('is_regression')
        has_source_bug = self.request.query_params.get('has_source_bug')
        tags = self.request.query_params.getlist('tags')
        search = self.request.query_params.get('search')

        if game_id:
            qs = qs.filter(game_id=game_id)
        if element_id:
            qs = qs.filter(element_id=element_id)
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        if tc_type:
            qs = qs.filter(tc_type_id=tc_type)
        if priority:
            qs = qs.filter(priority=priority)
        if is_regression == 'true':
            qs = qs.filter(is_regression=True)
        if is_regression == 'false':
            qs = qs.filter(is_regression=False)
        if has_source_bug == 'true':
            qs = qs.filter(source_bug__isnull=False)
        if has_source_bug == 'false':
            qs = qs.filter(source_bug__isnull=True)
        if tags:
            qs = qs.filter(tags__id__in=tags).distinct()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(code__icontains=search)
            )

        return qs.order_by('order_index', 'created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TestCaseWriteSerializer
        if self.action == 'retrieve':
            return TestCaseDetailSerializer
        return TestCaseListSerializer

    def destroy(self, request, *args, **kwargs):
        tc = self.get_object()
        tc.is_deleted = True
        tc.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Reorder TCs globally within an element.
        Accepts: [{"id": 1, "order_index": 0}, ...]
        """
        items = request.data.get('items', [])
        for item in items:
            TestCase.objects.filter(id=item['id']).update(
                order_index=item['order_index']
            )
        return Response({'status': 'reordered'})

    @action(detail=True, methods=['get'], url_path='prefill-from-bug')
    def prefill_from_bug(self, request, pk=None):
        """
        Returns structured pre-fill data for TC creation form
        when coming from a bug's 'Create TC' button.
        """
        tc = self.get_object()
        return Response({
            'title': tc.title,
            'steps': tc.steps,
            'expected_result': tc.expected_result,
            'element': tc.element_id,
            'element_code': tc.element.code if tc.element else None,
            'plan': tc.plan_id,
            'precondition': tc.precondition,
        })

    @action(detail=True, methods=['post'], url_path='finalize-regression-code')
    def finalize_regression_code(self, request, pk=None):
        """
        Sets the final regression TC code based on source TC code.
        Called after regression TC is created during a run.
        Format: {base_code}-R{N}
        """
        tc = self.get_object()
        if not tc.is_regression or not tc.source_bug:
            return Response(
                {'error': 'Not a regression TC'},
                status=status.HTTP_400_BAD_REQUEST
            )
        source_tc = tc.source_bug.source_tc
        if not source_tc:
            return Response(
                {'error': 'Source TC not found on bug'},
                status=status.HTTP_400_BAD_REQUEST
            )
        base_code = source_tc.code
        # Count existing regressions from same source
        n = TestCase.objects.filter(
            source_bug__source_tc=source_tc,
            is_regression=True
        ).exclude(id=tc.id).count() + 1
        tc.code = f'{base_code}-R{n}'
        tc.save()
        return Response({'code': tc.code})


# ── Test Plan ViewSet ─────────────────────────────────────────────────────────

class TestPlanViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = TestPlan.objects.filter(is_deleted=False).select_related('game')
        game_id = self.request.query_params.get('game')
        created_by = self.request.query_params.get('created_by')
        has_included = self.request.query_params.get('has_included_plans')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        search = self.request.query_params.get('search')

        if game_id:
            qs = qs.filter(game_id=game_id)
        if created_by:
            qs = qs.filter(created_by__icontains=created_by)
        if has_included == 'true':
            qs = qs.filter(included_plans__isnull=False).distinct()
        if has_included == 'false':
            qs = qs.filter(included_plans__isnull=True)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return TestPlanListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return TestPlanWriteSerializer
        return TestPlanDetailSerializer

    def destroy(self, request, *args, **kwargs):
        plan = self.get_object()
        plan.is_deleted = True
        plan.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='run-confirmation')
    def run_confirmation(self, request, pk=None):
        """
        Returns all data needed for the Run Start Confirmation Modal:
        plan info, current build version, full config snapshot,
        and any in-progress runs for different versions.
        """
        plan = self.get_object()
        game = plan.game
        config_snapshot = build_config_snapshot(plan)

        in_progress_other_versions = TestRun.objects.filter(
            game=game,
            status=TestRun.STATUS_IN_PROGRESS,
        ).exclude(
            build_version_snapshot=game.current_build_version
        ).values('id', 'code', 'build_version_snapshot', 'tester_name')

        return Response({
            'plan_id': plan.id,
            'plan_name': plan.name,
            'plan_code': plan.code,
            'plan_description': plan.description,
            'build_version': game.current_build_version,
            'game_config': config_snapshot,
            'in_progress_other_versions': list(in_progress_other_versions),
        })


# ── Plan Config Value ViewSet ─────────────────────────────────────────────────

class PlanConfigValueViewSet(viewsets.ModelViewSet):
    serializer_class = PlanConfigValueSerializer

    def get_queryset(self):
        qs = PlanConfigValue.objects.select_related('config_field')
        plan_id = self.request.query_params.get('plan')
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs

    @action(detail=False, methods=['get'], url_path='for-plan')
    def for_plan(self, request):
        """
        Returns all config fields for a game with plan-scoped values
        merged in (falls back to game default where plan has no value).
        """
        plan_id = request.query_params.get('plan')
        if not plan_id:
            return Response({'error': 'plan param required'},
                            status=status.HTTP_400_BAD_REQUEST)
        plan = TestPlan.objects.get(id=plan_id)
        config_fields = GameConfigField.objects.filter(game=plan.game).order_by(
            'order_index', 'created_at'
        )
        plan_values = {
            pv.config_field_id: pv.value
            for pv in PlanConfigValue.objects.filter(plan=plan)
        }
        result = []
        for field in config_fields:
            result.append({
                'config_field_id': field.id,
                'name': field.name,
                'group_label': field.group_label,
                'field_type': field.field_type,
                'constraints': field.constraints,
                'default_value': field.default_value,
                'plan_value': plan_values.get(field.id),
                'effective_value': plan_values.get(field.id, field.default_value),
                'plan_config_value_id': next(
                    (pv.id for pv in PlanConfigValue.objects.filter(
                        plan=plan, config_field=field
                    )), None
                ),
            })
        return Response(result)


# ── Plan Item ViewSet ─────────────────────────────────────────────────────────

class PlanItemViewSet(viewsets.ModelViewSet):
    serializer_class = PlanItemSerializer

    def get_queryset(self):
        qs = PlanItem.objects.select_related('element', 'element__element_type')
        plan_id = self.request.query_params.get('plan')
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs.order_by('order_index')

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        # Append to bottom
        last = PlanItem.objects.filter(plan=plan).order_by('-order_index').first()
        next_order = (last.order_index + 1) if last else 0
        serializer.save(order_index=next_order)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """Reorder elements within a plan."""
        items = request.data.get('items', [])
        for item in items:
            PlanItem.objects.filter(id=item['id']).update(
                order_index=item['order_index']
            )
        return Response({'status': 'reordered'})

    @action(detail=True, methods=['get'], url_path='available-tcs')
    def available_tcs(self, request, pk=None):
        """
        Returns all TCs available for selection under this element in this plan:
        - Element-only TCs (global, reusable)
        - Element+Plan TCs scoped to this plan
        Supports tag/type/priority filtering.
        """
        plan_item = self.get_object()
        qs = TestCase.objects.filter(
            is_deleted=False,
            element=plan_item.element,
        ).filter(
            Q(plan__isnull=True) | Q(plan=plan_item.plan)
        )

        tags = request.query_params.getlist('tags')
        tc_type = request.query_params.get('tc_type')
        priority = request.query_params.get('priority')
        search = request.query_params.get('search')

        if tags:
            qs = qs.filter(tags__id__in=tags).distinct()
        if tc_type:
            qs = qs.filter(tc_type_id=tc_type)
        if priority:
            qs = qs.filter(priority=priority)
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(code__icontains=search)
            )

        # Mark which are already selected in this plan
        selected_ids = set(
            PlanItemTC.objects.filter(
                plan=plan_item.plan, element=plan_item.element
            ).values_list('test_case_id', flat=True)
        )

        result = []
        for tc in qs.order_by('order_index', 'created_at'):
            data = TestCaseListSerializer(tc).data
            data['selected'] = tc.id in selected_ids
            result.append(data)

        return Response(result)


# ── Plan Item TC ViewSet ──────────────────────────────────────────────────────

class PlanItemTCViewSet(viewsets.ModelViewSet):
    serializer_class = PlanItemTCSerializer

    def get_queryset(self):
        qs = PlanItemTC.objects.select_related('test_case', 'test_case__tc_type')
        plan_id = self.request.query_params.get('plan')
        element_id = self.request.query_params.get('element')
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        if element_id:
            qs = qs.filter(element_id=element_id)
        return qs.order_by('order_index')

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        element = serializer.validated_data['element']
        # Initialize order from global TC order_index
        tc = serializer.validated_data['test_case']
        last = PlanItemTC.objects.filter(plan=plan, element=element).order_by(
            '-order_index'
        ).first()
        next_order = (last.order_index + 1) if last else tc.order_index
        serializer.save(order_index=next_order)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """Reorder TCs within an element within a plan."""
        items = request.data.get('items', [])
        for item in items:
            PlanItemTC.objects.filter(id=item['id']).update(
                order_index=item['order_index']
            )
        return Response({'status': 'reordered'})


# ── Plan TC ViewSet ───────────────────────────────────────────────────────────

class PlanTCViewSet(viewsets.ModelViewSet):
    serializer_class = PlanTCSerializer

    def get_queryset(self):
        qs = PlanTC.objects.select_related('test_case')
        plan_id = self.request.query_params.get('plan')
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return qs.order_by('order_index')

    def perform_create(self, serializer):
        plan = serializer.validated_data['plan']
        last = PlanTC.objects.filter(plan=plan).order_by('-order_index').first()
        next_order = (last.order_index + 1) if last else 0
        serializer.save(order_index=next_order)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        items = request.data.get('items', [])
        for item in items:
            PlanTC.objects.filter(id=item['id']).update(
                order_index=item['order_index']
            )
        return Response({'status': 'reordered'})


# ── Plan Includes ViewSet ─────────────────────────────────────────────────────

class PlanIncludesViewSet(viewsets.ModelViewSet):
    serializer_class = PlanIncludesSerializer

    def get_queryset(self):
        qs = PlanIncludes.objects.select_related('child_plan')
        parent_plan_id = self.request.query_params.get('parent_plan')
        if parent_plan_id:
            qs = qs.filter(parent_plan_id=parent_plan_id)
        return qs

    def validate_no_cycle(self, parent_plan, child_plan):
        """Prevent circular plan includes."""
        visited = set()
        queue = [child_plan.id]
        while queue:
            current_id = queue.pop()
            if current_id == parent_plan.id:
                return False
            if current_id in visited:
                continue
            visited.add(current_id)
            children = PlanIncludes.objects.filter(
                parent_plan_id=current_id
            ).values_list('child_plan_id', flat=True)
            queue.extend(children)
        return True

    def create(self, request, *args, **kwargs):
        parent_plan_id = request.data.get('parent_plan')
        child_plan_id = request.data.get('child_plan')
        try:
            parent_plan = TestPlan.objects.get(id=parent_plan_id)
            child_plan = TestPlan.objects.get(id=child_plan_id)
        except TestPlan.DoesNotExist:
            return Response({'error': 'Plan not found'},
                            status=status.HTTP_404_NOT_FOUND)

        if parent_plan.game_id != child_plan.game_id:
            return Response(
                {'error': 'Both plans must belong to the same game'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not self.validate_no_cycle(parent_plan, child_plan):
            return Response(
                {'error': 'Circular plan inclusion detected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)


# ── Plan Include Exclusion ViewSet ────────────────────────────────────────────

class PlanIncludeExclusionViewSet(viewsets.ModelViewSet):
    serializer_class = PlanIncludeExclusionSerializer

    def get_queryset(self):
        qs = PlanIncludeExclusion.objects.all()
        inclusion_id = self.request.query_params.get('inclusion')
        if inclusion_id:
            qs = qs.filter(inclusion_id=inclusion_id)
        return qs


# ── Test Run ViewSet ──────────────────────────────────────────────────────────

class TestRunViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = TestRun.objects.select_related('game', 'plan').order_by('-started_at')
        game_id = self.request.query_params.get('game')
        plan_id = self.request.query_params.get('plan')
        status_filter = self.request.query_params.get('status')
        version = self.request.query_params.get('version')
        tester = self.request.query_params.get('tester')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        search = self.request.query_params.get('search')

        if game_id:
            qs = qs.filter(game_id=game_id)
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if version:
            qs = qs.filter(build_version_snapshot=version)
        if tester:
            qs = qs.filter(tester_name__icontains=tester)
        if date_from:
            qs = qs.filter(started_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(started_at__date__lte=date_to)
        if search:
            qs = qs.filter(code__icontains=search)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestRunDetailSerializer
        return TestRunListSerializer

    def create(self, request, *args, **kwargs):
        """
        Starts a new test run:
        1. Resolves TC list from plan (including live-synced included plans)
        2. Snapshots build version and game config
        3. Creates RunEntry for each TC in order
        4. Logs Run Started audit entry
        """
        plan_id = request.data.get('plan')
        tester_name = request.data.get('tester_name', '')

        try:
            plan = TestPlan.objects.get(id=plan_id, is_deleted=False)
        except TestPlan.DoesNotExist:
            return Response({'error': 'Plan not found'},
                            status=status.HTTP_404_NOT_FOUND)

        game = plan.game
        build_version = game.current_build_version
        config_snapshot = build_config_snapshot(plan)
        tc_list = resolve_plan_tcs(plan)
        tc_order_snapshot = [item['tc_id'] for item in tc_list]

        run = TestRun.objects.create(
            game=game,
            plan=plan,
            build_version_snapshot=build_version,
            game_config_snapshot=config_snapshot,
            tc_order_snapshot=tc_order_snapshot,
            tester_name=tester_name,
            status=TestRun.STATUS_IN_PROGRESS,
        )

        # Create RunEntries for all TCs in resolved order
        for item in tc_list:
            try:
                tc = TestCase.objects.get(id=item['tc_id'], is_deleted=False)
            except TestCase.DoesNotExist:
                continue

            element = tc.element
            RunEntry.objects.create(
                run=run,
                test_case=tc,
                expected_result_snapshot=tc.expected_result,
                steps_snapshot=tc.steps,
                element_purpose_snapshot=element.purpose if element else [],
                element_precondition_snapshot=element.precondition if element else '',
                added_during_run=False,
            )

        # Audit
        audit(run, AuditEntry.EVENT_RUN_STARTED, {
            'plan_name': plan.name,
            'plan_code': plan.code,
            'build_version': build_version,
            'config_summary': {k: v['value'] for k, v in config_snapshot.items()},
            'tc_count': len(tc_list),
        }, tester_name)

        return Response(
            TestRunDetailSerializer(run).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        run = self.get_object()
        if run.status != TestRun.STATUS_IN_PROGRESS:
            return Response(
                {'error': 'Only In Progress runs can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        run.status = TestRun.STATUS_COMPLETE
        run.ended_at = timezone.now()
        run.save()
        audit(run, AuditEntry.EVENT_RUN_COMPLETED, {
            'final_status': run.status,
            'total_duration_sec': int(
                (run.ended_at - run.started_at).total_seconds()
            ),
        }, request.data.get('tester_name', run.tester_name))
        return Response(TestRunDetailSerializer(run).data)

    @action(detail=True, methods=['post'], url_path='abandon')
    def abandon(self, request, pk=None):
        run = self.get_object()
        if run.status != TestRun.STATUS_IN_PROGRESS:
            return Response(
                {'error': 'Only In Progress runs can be abandoned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        run.status = TestRun.STATUS_ABANDONED
        run.ended_at = timezone.now()
        run.save()
        audit(run, AuditEntry.EVENT_RUN_ABANDONED, {
            'timestamp': run.ended_at.isoformat(),
        }, request.data.get('tester_name', run.tester_name))
        return Response(TestRunDetailSerializer(run).data)


# ── Run Entry ViewSet ─────────────────────────────────────────────────────────

class RunEntryViewSet(viewsets.ModelViewSet):
    serializer_class = RunEntrySerializer

    def get_queryset(self):
        qs = RunEntry.objects.select_related(
            'test_case', 'test_case__element', 'test_case__tc_type', 'run'
        )
        run_id = self.request.query_params.get('run')
        if run_id:
            qs = qs.filter(run_id=run_id)
        return qs.order_by('created_at')

    @action(detail=True, methods=['post'], url_path='open')
    def open_entry(self, request, pk=None):
        """Records the timestamp when tester opens a TC during a run."""
        entry = self.get_object()
        if not entry.opened_at:
            entry.opened_at = timezone.now()
            entry.save()
            audit(entry.run, AuditEntry.EVENT_TC_OPENED, {
                'tc_code': entry.test_case.code,
                'tc_title': entry.test_case.title,
                'priority': entry.test_case.priority,
                'type': entry.test_case.tc_type.name if entry.test_case.tc_type else None,
                'element_code': entry.test_case.element.code if entry.test_case.element else None,
            }, request.data.get('tester_name', entry.run.tester_name))
        return Response(RunEntrySerializer(entry).data)

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        """
        Submits a TC result.
        Calculates time_taken_sec from opened_at to now.
        Logs audit entry.
        """
        entry = self.get_object()
        result_status = request.data.get('status')
        actual_result = request.data.get('actual_result', '')
        notes = request.data.get('notes', '')
        tester_name = request.data.get(
            'tester_name', entry.run.tester_name
        )

        valid_statuses = ['Pass', 'Fail', 'Blocked', 'Skip']
        if result_status not in valid_statuses:
            return Response(
                {'error': f'status must be one of {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not actual_result:
            return Response(
                {'error': 'actual_result is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        entry.status = result_status
        entry.actual_result = actual_result
        entry.notes = notes
        entry.submitted_at = now

        if entry.opened_at:
            delta = now - entry.opened_at
            entry.time_taken_sec = int(delta.total_seconds())

        entry.save()

        audit(entry.run, AuditEntry.EVENT_TC_RESULT, {
            'tc_code': entry.test_case.code,
            'tc_title': entry.test_case.title,
            'status': result_status,
            'actual_result': actual_result[:200],
            'time_taken_sec': entry.time_taken_sec,
        }, tester_name)

        return Response(RunEntrySerializer(entry).data)


# ── Bug ViewSet ───────────────────────────────────────────────────────────────

class BugViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        qs = Bug.objects.select_related(
            'element', 'bug_type', 'test_run', 'run_entry', 'game'
        )
        game_id = self.request.query_params.get('game')
        element_id = self.request.query_params.get('element')
        severity = self.request.query_params.get('severity')
        priority = self.request.query_params.get('priority')
        bug_type = self.request.query_params.get('bug_type')
        repro = self.request.query_params.get('reproducibility')
        version = self.request.query_params.get('version')
        reporter = self.request.query_params.get('reporter')
        is_exploratory = self.request.query_params.get('is_exploratory')
        has_linked_tc = self.request.query_params.get('has_linked_tc')
        bug_status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if game_id:
            qs = qs.filter(game_id=game_id)
        if element_id:
            qs = qs.filter(element_id=element_id)
        if severity:
            qs = qs.filter(severity=severity)
        if priority:
            qs = qs.filter(priority=priority)
        if bug_type:
            qs = qs.filter(bug_type_id=bug_type)
        if repro:
            qs = qs.filter(reproducibility=repro)
        if version:
            qs = qs.filter(build_version_snapshot=version)
        if reporter:
            qs = qs.filter(reporter__icontains=reporter)
        if is_exploratory == 'true':
            qs = qs.filter(is_exploratory=True)
        if is_exploratory == 'false':
            qs = qs.filter(is_exploratory=False)
        if has_linked_tc == 'true':
            qs = qs.exclude(linked_tc_codes=[])
        if has_linked_tc == 'false':
            qs = qs.filter(linked_tc_codes=[])
        if bug_status:
            qs = qs.filter(status=bug_status)
        if search:
            qs = qs.filter(
                Q(code__icontains=search) | Q(summary__icontains=search)
            )

        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BugWriteSerializer
        if self.action == 'retrieve':
            return BugDetailSerializer
        return BugListSerializer

    def create(self, request, *args, **kwargs):
        """
        Creates a bug. Handles all 3 sources:
        A) From failed RunEntry — is_exploratory=False
        B) Exploratory during run — is_exploratory=True, run linked
        C) Standalone — is_exploratory=True, no run
        """
        data = request.data
        run_entry_id = data.get('run_entry')
        test_run_id = data.get('test_run')
        is_exploratory = data.get('is_exploratory', False)
        reporter = data.get('reporter', '')
        tester_name = reporter

        # Determine build version snapshot
        build_version = ''
        if run_entry_id:
            try:
                run_entry = RunEntry.objects.get(id=run_entry_id)
                build_version = run_entry.run.build_version_snapshot
                test_run_id = run_entry.run_id
            except RunEntry.DoesNotExist:
                pass
        elif test_run_id:
            try:
                test_run = TestRun.objects.get(id=test_run_id)
                build_version = test_run.build_version_snapshot
            except TestRun.DoesNotExist:
                pass
        else:
            try:
                game = Game.objects.get(id=data.get('game'))
                build_version = game.current_build_version
            except Game.DoesNotExist:
                pass

        serializer = BugWriteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        bug = serializer.save(
            is_exploratory=is_exploratory,
            build_version_snapshot=build_version,
            reporter=reporter,
            run_entry_id=run_entry_id,
            test_run_id=test_run_id,
            source_tc_id=data.get('source_tc'),
            source_plan_id=data.get('source_plan'),
        )

        # Audit if during a run
        if test_run_id:
            try:
                run = TestRun.objects.get(id=test_run_id)
                audit(run, AuditEntry.EVENT_BUG_FILED, {
                    'bug_code': bug.code,
                    'summary': bug.summary,
                    'element': bug.element.code if bug.element else 'No Element',
                    'severity': bug.severity,
                    'source': 'Exploratory' if is_exploratory else 'Fail',
                }, tester_name)
            except TestRun.DoesNotExist:
                pass

        return Response(BugDetailSerializer(bug).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """Kanban drag — update bug status."""
        bug = self.get_object()
        new_status = request.data.get('status')
        valid = [s[0] for s in Bug.STATUS_CHOICES]
        if new_status not in valid:
            return Response(
                {'error': f'status must be one of {valid}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        bug.status = new_status
        bug.save()
        return Response(BugListSerializer(bug).data)

    @action(detail=True, methods=['get'], url_path='tc-prefill')
    def tc_prefill(self, request, pk=None):
        """
        Returns pre-fill data for TC creation form when coming from a bug.
        """
        bug = self.get_object()
        return Response({
            'title': bug.summary,
            'steps': bug.steps,
            'expected_result': bug.description,
            'element': bug.element_id,
            'element_code': bug.element.code if bug.element else None,
            'plan': bug.source_plan_id,
            'precondition': bug.element.precondition if bug.element else '',
            'source_bug_id': bug.id,
            'source_bug_code': bug.code,
        })

    @action(detail=True, methods=['post'], url_path='link-tc')
    def link_tc(self, request, pk=None):
        """
        Called after a TC is created from this bug.
        Appends TC code to bug's linked_tc_codes array.
        Also logs audit if during a run.
        """
        bug = self.get_object()
        tc_code = request.data.get('tc_code')
        tc_id = request.data.get('tc_id')
        tester_name = request.data.get('tester_name', bug.reporter)

        if not tc_code:
            return Response({'error': 'tc_code required'},
                            status=status.HTTP_400_BAD_REQUEST)

        codes = bug.linked_tc_codes or []
        if tc_code not in codes:
            codes.append(tc_code)
            bug.linked_tc_codes = codes
            bug.save()

        # Audit if bug is linked to a run
        if bug.test_run_id:
            try:
                audit(bug.test_run, AuditEntry.EVENT_TC_LINKED, {
                    'tc_code': tc_code,
                    'bug_code': bug.code,
                }, tester_name)
            except Exception:
                pass

        return Response({'linked_tc_codes': bug.linked_tc_codes})


# ── Attachment ViewSet ────────────────────────────────────────────────────────

class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentSerializer

    def get_queryset(self):
        qs = Attachment.objects.all()
        run_entry_id = self.request.query_params.get('run_entry')
        bug_id = self.request.query_params.get('bug')
        if run_entry_id:
            qs = qs.filter(run_entry_id=run_entry_id)
        if bug_id:
            qs = qs.filter(bug_id=bug_id)
        return qs.order_by('uploaded_at')

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if file:
            serializer.save(
                file_name=file.name,
                file_type=file.content_type,
            )
        else:
            serializer.save()


# ── Audit ViewSet ─────────────────────────────────────────────────────────────

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEntrySerializer

    def get_queryset(self):
        qs = AuditEntry.objects.select_related('run')
        run_id = self.request.query_params.get('run')
        if run_id:
            qs = qs.filter(run_id=run_id)
        return qs.order_by('timestamp')


# ── Global Search ViewSet ─────────────────────────────────────────────────────

class GlobalSearchViewSet(viewsets.ViewSet):

    def list(self, request):
        q = request.query_params.get('q', '').strip()
        game_id = request.query_params.get('game')

        if not q or len(q) < 2:
            return Response({'elements': [], 'test_cases': [],
                             'bugs': [], 'plans': []})

        results = {'elements': [], 'test_cases': [], 'bugs': [], 'plans': []}

        elem_qs = Element.objects.filter(
            is_deleted=False
        ).filter(Q(name__icontains=q) | Q(code__icontains=q))
        if game_id:
            elem_qs = elem_qs.filter(game_id=game_id)
        for e in elem_qs[:20]:
            results['elements'].append({
                'type': 'Element',
                'id': e.id,
                'code': e.code,
                'title': e.name,
                'context': e.element_type.name,
                'url': f'/elements/{e.id}/',
            })

        tc_qs = TestCase.objects.filter(
            is_deleted=False
        ).filter(Q(title__icontains=q) | Q(code__icontains=q))
        if game_id:
            tc_qs = tc_qs.filter(game_id=game_id)
        for tc in tc_qs[:20]:
            results['test_cases'].append({
                'type': 'Test Case',
                'id': tc.id,
                'code': tc.code,
                'title': tc.title,
                'context': tc.element.name if tc.element else 'Plan-only',
                'url': f'/test-cases/{tc.id}/',
            })

        bug_qs = Bug.objects.filter(
            Q(summary__icontains=q) | Q(code__icontains=q)
        )
        if game_id:
            bug_qs = bug_qs.filter(game_id=game_id)
        for b in bug_qs[:20]:
            results['bugs'].append({
                'type': 'Bug',
                'id': b.id,
                'code': b.code,
                'title': b.summary,
                'context': b.element.name if b.element else 'No Element',
                'url': f'/bugs/{b.id}/',
            })

        plan_qs = TestPlan.objects.filter(
            is_deleted=False
        ).filter(Q(name__icontains=q) | Q(code__icontains=q))
        if game_id:
            plan_qs = plan_qs.filter(game_id=game_id)
        for p in plan_qs[:20]:
            results['plans'].append({
                'type': 'Test Plan',
                'id': p.id,
                'code': p.code,
                'title': p.name,
                'context': p.game.name,
                'url': f'/plans/{p.id}/',
            })

        return Response(results)
