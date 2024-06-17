from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChannelViewSet, SecretExchangeView, KeyGenerationView

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='channel')

urlpatterns = [
    path('', include(router.urls)),  # Includes all routes defined in the router.
    path('secret_exchange/<int:channel_id>/', SecretExchangeView.as_view(), name='secret_exchange'),
    path('key_generation/<int:channel_id>/', KeyGenerationView.as_view(), name='key_generation'),
]
