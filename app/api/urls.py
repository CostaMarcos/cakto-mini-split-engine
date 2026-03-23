from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HealthCheckViewSet

router = DefaultRouter()
router.register(r'health', HealthCheckViewSet, basename='health')

urlpatterns = [
    path('', include(router.urls)),
]
