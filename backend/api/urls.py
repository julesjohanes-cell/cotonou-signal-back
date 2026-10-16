from django.urls import path
from .views import health_check, get_features

urlpatterns = [
    path('health/', health_check, name='api-health'),
    path('features/', get_features, name='api-features'),
]
