# cart/views.py
from rest_framework import generics, permissions
from .models import CartItem
from .serializers import CartItemSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CartItemListCreateView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart_summary(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)

    total_items = sum(item.quantity for item in cart_items)
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    return Response({
        "total_items": total_items,
        "total_price": round(total_price, 2)
    })