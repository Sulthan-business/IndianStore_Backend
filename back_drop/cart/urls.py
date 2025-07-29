from django.urls import path
from .views import CartItemListCreateView, CartItemDetailView, get_cart_summary

urlpatterns = [
    path('', CartItemListCreateView.as_view(), name='cart-list-create'),
    path('<int:pk>/', CartItemDetailView.as_view(), name='cart-detail'),
    path('summary/', get_cart_summary, name='cart-summary'),  # ✅ no need to call views.get_cart_summary
]
