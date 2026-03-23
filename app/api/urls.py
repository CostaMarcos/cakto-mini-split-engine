from django.urls import path
from .views import CheckoutQuoteView, PaymentView

urlpatterns = [
    path('checkout/quote/', CheckoutQuoteView.as_view(), name='checkout-quote'),
    path('payments/', PaymentView.as_view(), name='payment-create'),
]
