from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, generics, permissions
from .models import Order, OrderItem
from .serializers import OrderSerializer
from cart.models import CartItem
from decimal import Decimal

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-ordered_at')

class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
def post(self, request):
    print("✅ Checkout POST hit")
    ...

    def post(self, request):
        user = request.user
        cart_items = CartItem.objects.filter(user=user)

        if not cart_items.exists():
            return Response({"detail": "Cart is empty."}, status=400)

        total = Decimal('0.00')
        for item in cart_items:
            total += item.product.price * item.quantity

        order = Order.objects.create(
            user=user,
            total_price=total,
            customer_name=user.username,
            customer_email=user.email
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
                total_price=item.product.price * item.quantity
            )

        cart_items.delete()

        return Response({
            "detail": "Order placed successfully",
            "order_id": order.id
        })
