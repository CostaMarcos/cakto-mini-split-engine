from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HealthCheckViewSet, CheckoutQuoteView

router = DefaultRouter()
router.register(r'health', HealthCheckViewSet, basename='health')

urlpatterns = [
    path('', include(router.urls)),
    path('checkout/quote/', CheckoutQuoteView.as_view(), name='checkout-quote'),
]
