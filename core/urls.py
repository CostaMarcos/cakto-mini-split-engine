from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('api/v1/', include('app.api.urls')),
    path('', lambda request: redirect('api/v1/')),
]
