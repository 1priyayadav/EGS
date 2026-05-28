from django.urls import path, include
from rest_framework.routers import DefaultRouter
from emissions.views import EmissionRecordViewSet, IngestionViewSet

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='emissionrecord')
router.register(r'ingestion', IngestionViewSet, basename='ingestion')

urlpatterns = [
    path('', include(router.urls)),
]
