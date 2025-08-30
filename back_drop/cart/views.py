# cart/views.py
from rest_framework import generics, permissions
from .models import CartItem
from .serializers import CartItemSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse,OpenApiExample
from common.permissions import IsOwner 
@extend_schema_view(
    get=extend_schema(
        tags=["Cart"],
        summary="List my cart items",
        responses={200: OpenApiResponse(response=CartItemSerializer(many=True))}
    ),
    post=extend_schema(
        tags=["Cart"],
        summary="Add item to my cart",
        request=CartItemSerializer,
        responses={201: OpenApiResponse(response=CartItemSerializer)}
    ),
)
@extend_schema(exclude=True)
class CartItemListCreateView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    get=extend_schema(tags=["Cart"], summary="Retrieve a cart item"),
    put=extend_schema(tags=["Cart"], summary="Replace a cart item"),
    patch=extend_schema(tags=["Cart"], summary="Update a cart item"),
    delete=extend_schema(tags=["Cart"], summary="Remove a cart item"),
)
class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

@extend_schema(
    tags=["Cart"],
    summary="Cart summary (items & total)",
    responses={
        200: {
            "type": "object",
            "properties": {
                "total_items": {"type": "integer"},
                "total_price": {"type": "number", "format": "float"},
            },
            "example": {"total_items": 3, "total_price": 2499.00},
        }
    },
    examples=[
        OpenApiExample(
            "Empty cart",
            value={"total_items": 0, "total_price": 0.0}
        )
    ]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart_summary(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    total_items = sum(item.quantity for item in cart_items)
    total_price = float(sum(item.product.price * item.quantity for item in cart_items))
    return Response({"total_items": total_items, "total_price": round(total_price, 2)})