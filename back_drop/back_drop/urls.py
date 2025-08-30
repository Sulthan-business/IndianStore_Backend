# back_drop/urls.py  ✅ final ordering

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from products.views import ProductViewSet
from rest_framework.views import exception_handler as drf_handler
from orders.views import OrderViewSet, CheckoutView, PaymentWebhookView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)  # keep if you want list/detail CRUD

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT first or anywhere; doesn’t matter for this issue
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 👇 Place custom endpoints BEFORE the router
    path('api/orders/checkout/', CheckoutView.as_view(), name='order-checkout'),
    path('api/orders/', include('orders.urls')),  # my-orders, create, etc.

    # Now the router (was previously first — that caused the 405)
    path('api/', include(router.urls)),

    # Other apps
    path('api/users/', include('users.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/', include('rest_framework.urls')),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),


     # checkout + payments
    path('api/orders/checkout/', CheckoutView.as_view(), name='order-checkout'),
    path('api/payments/webhook/', PaymentWebhookView.as_view(), name='payments-webhook'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
def custom_exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is not None and isinstance(response.data, dict):
        response.data = {"error": True, "detail": response.data.get("detail", response.data)}
    return response
