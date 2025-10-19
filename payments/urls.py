from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    CartAPIView, CheckoutAPIView, StripeWebhookAPIView, StripePublishableKeyAPIView,
    CartPageView, CheckoutPageView
)
from django.conf import settings
from django.http import JsonResponse

def health(request):
    """
    Basic health/config check for local debugging:
    - stripe_ok: both secret & publishable keys present
    - webhook_ok: webhook secret present
    - db_configured: DB name present in settings
    - s3_enabled: USE_S3 flag
    - allowed_hosts: current ALLOWED_HOSTS
    """
    stripe_ok = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY)
    webhook_ok = bool(settings.STRIPE_WEBHOOK_SECRET)
    db_name = settings.DATABASES.get('default', {}).get('NAME')
    db_configured = bool(db_name)
    return JsonResponse({
        "ok": True,
        "stripe_ok": stripe_ok,
        "webhook_ok": webhook_ok,
        "db_configured": db_configured,
        "s3_enabled": bool(getattr(settings, "USE_S3", False)),
        "allowed_hosts": settings.ALLOWED_HOSTS,
    })

urlpatterns = [
    # Page UI
    path('cart/', CartPageView.as_view(), name='cart-page'),
    path('checkout/', CheckoutPageView.as_view(), name='checkout-page'),

    # API endpoints
    path('api/cart/', CartAPIView.as_view(), name='cart-api'),
    path('api/checkout/', CheckoutAPIView.as_view(), name='checkout-api'),
    path('api/stripe-key/', StripePublishableKeyAPIView.as_view(), name='stripe-key'),
    path('stripe/webhook/', StripeWebhookAPIView.as_view(), name='stripe-webhook'),
    path('api/health/', health, name='payments-health'),
    # JWT token endpoints for mobile clients
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
