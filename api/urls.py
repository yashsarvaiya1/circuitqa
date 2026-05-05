# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.viewsets import (
    PlatformViewSet, GenreViewSet, ElementTypeViewSet, RelationTypeViewSet,
    TestCaseTypeViewSet, BugTypeViewSet, ConfigFieldTypeViewSet, TagViewSet,
    GameViewSet, GameConfigFieldViewSet,
    ElementViewSet, RelatedElementViewSet,
    TestCaseViewSet, TestPlanViewSet,
    PlanConfigValueViewSet, PlanItemViewSet, PlanItemTCViewSet,
    PlanTCViewSet, PlanIncludesViewSet, PlanIncludeExclusionViewSet,
    TestRunViewSet, RunEntryViewSet,
    BugViewSet, AttachmentViewSet, AuditViewSet, GlobalSearchViewSet,
)

router = DefaultRouter()
router.register(r'platforms', PlatformViewSet, basename='platform')
router.register(r'genres', GenreViewSet, basename='genre')
router.register(r'element-types', ElementTypeViewSet, basename='element-type')
router.register(r'relation-types', RelationTypeViewSet, basename='relation-type')
router.register(r'tc-types', TestCaseTypeViewSet, basename='tc-type')
router.register(r'bug-types', BugTypeViewSet, basename='bug-type')
router.register(r'config-field-types', ConfigFieldTypeViewSet, basename='config-field-type')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'games', GameViewSet, basename='game')
router.register(r'config-fields', GameConfigFieldViewSet, basename='config-field')
router.register(r'elements', ElementViewSet, basename='element')
router.register(r'related-elements', RelatedElementViewSet, basename='related-element')
router.register(r'test-cases', TestCaseViewSet, basename='test-case')
router.register(r'plans', TestPlanViewSet, basename='plan')
router.register(r'plan-config-values', PlanConfigValueViewSet, basename='plan-config-value')
router.register(r'plan-items', PlanItemViewSet, basename='plan-item')
router.register(r'plan-item-tcs', PlanItemTCViewSet, basename='plan-item-tc')
router.register(r'plan-tcs', PlanTCViewSet, basename='plan-tc')
router.register(r'plan-includes', PlanIncludesViewSet, basename='plan-includes')
router.register(r'plan-exclusions', PlanIncludeExclusionViewSet, basename='plan-exclusion')
router.register(r'runs', TestRunViewSet, basename='run')
router.register(r'run-entries', RunEntryViewSet, basename='run-entry')
router.register(r'bugs', BugViewSet, basename='bug')
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'audit', AuditViewSet, basename='audit')
router.register(r'search', GlobalSearchViewSet, basename='search')

urlpatterns = [
    path('', include(router.urls)),
]
