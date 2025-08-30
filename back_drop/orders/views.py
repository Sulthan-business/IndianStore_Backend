# orders/views.py
from decimal import Decimal
import logging

from django.db import transaction
from django.db.models import F

from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import (
    extend_schema_view, extend_schema, OpenApiResponse, OpenApiExample
)

from .models import Order, OrderItem, Payment
from .serializers import OrderSerializer
from cart.models import CartItem
from common.permissions import IsOwner

logger = logging.getLogger(__name__)


# ---------- ORDERS CRUD ----------
@extend_schema_view(
    list=extend_schema(tags=["Orders"]),
    retrieve=extend_schema(tags=["Orders"]),
    create=extend_schema(tags=["Orders"]),
    update=extend_schema(tags=["Orders"]),
    partial_update=extend_schema(tags=["Orders"]),
    destroy=extend_schema(tags=["Orders"]),
)
class OrderViewSet(viewsets.ModelViewSet):
    """
    Owner-scoped CRUD for orders.
    """
    lookup_value_regex = r"\d+"  # only numeric IDs for <pk>
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = Order.objects.all().order_by("-ordered_at")

    def get_queryset(self):
        # Never expose other users' orders
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-ordered_at")


# ---------- CHECKOUT ----------
@extend_schema(
    tags=["Orders"],
    request=None,
    responses={
        201: OpenApiResponse(description="Order created"),
        400: OpenApiResponse(description="Cart is empty / invalid input"),
        401: OpenApiResponse(description="Unauthorized"),
    },
    examples=[
        OpenApiExample(
            "COD Success",
            value={"detail": "Order placed successfully (COD)", "order_id": 42},
            response_only=True,
            status_codes=["201"],
        ),
        OpenApiExample(
            "Online Pending",
            value={
                "detail": "Payment pending",
                "order_id": 42,
                "pg_order_id": "stub_42",
                "amount": "999.99",
            },
            response_only=True,
            status_codes=["201"],
        ),
        OpenApiExample(
            "Empty cart",
            value={"detail": "Cart is empty."},
            response_only=True,
            status_codes=["400"],
        ),
    ],
)
class CheckoutView(APIView):
    """
    Converts the authenticated user's cart into an order.
    Supports:
      - COD (only if all items allow COD)
      - ONLINE (stub provider until real gateway integrated)

    Stock checks are optional: if product has a 'stock' field, it's validated
    and decremented atomically using F() updates.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Orders"],
        operation_id="orders_checkout",
        summary="Checkout cart into an order",
        description=(
            "Converts the authenticated user's cart items into an order. "
            "If payment_method='ONLINE', creates a stub payment and returns a gateway order id; "
            "cart remains until payment is captured via webhook. "
            "If payment_method='COD', order is placed immediately and cart is cleared."
        ),
    )
    def dispatch(self, request, *args, **kwargs):
        logger.debug("CheckoutView.dispatch reached")
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request):
        user = request.user

        # Lock user's cart rows for safe totals/stock operations
        cart_items = (
            CartItem.objects
            .select_related("product")
            .select_for_update()
            .filter(user=user)
        )

        if not cart_items.exists():
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Client-selected method
        method = (request.data.get("payment_method") or "ONLINE").upper()
        if method not in ("COD", "ONLINE"):
            return Response({"detail": "Invalid payment_method"}, status=status.HTTP_400_BAD_REQUEST)

        # COD eligibility: all items must allow COD
        cod_allowed = all(
            getattr(item.product, "cod_available", False)
            for item in cart_items
        )
        if method == "COD" and not cod_allowed:
            return Response(
                {"detail": "COD not available for one or more items in your cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional stock checks (only if product has 'stock')
        for it in cart_items:
            if hasattr(it.product, "stock"):
                if it.product.stock < it.quantity:
                    return Response(
                        {"detail": f"Not enough stock for {getattr(it.product, 'name', str(it.product))}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Totals
        total = Decimal("0.00")
        for it in cart_items:
            total += (it.product.price * it.quantity)

        # Create order
        order = Order.objects.create(
            user=user,
            total_price=total,
            payment_method=method,
            payment_status=(
                Order.PaymentStatus.COD_PENDING if method == "COD"
                else Order.PaymentStatus.PENDING
            ),
            status=(
                Order.Status.PLACED if method == "COD"
                else Order.Status.PAYMENT_PENDING
            ),
            cod_allowed_snapshot=cod_allowed,
            customer_name=getattr(user, "username", "") or getattr(user, "get_full_name", lambda: "")(),
            customer_email=getattr(user, "email", ""),
        )

        # Create order items (bulk)
        order_items = []
        for it in cart_items:
            order_items.append(OrderItem(
                order=order,
                product=it.product,
                quantity=it.quantity,
                unit_price=it.product.price,
                total_price=it.product.price * it.quantity,
            ))
        OrderItem.objects.bulk_create(order_items)

        # Decrement stock atomically if present
        for it in cart_items:
            if hasattr(it.product, "stock"):
                # Avoid hard import of Product; use the concrete model class
                it.product.__class__.objects.filter(pk=it.product_id).update(stock=F("stock") - it.quantity)

        # Handle payment flows
        if method == "ONLINE":
            # Create stub payment record (replace with real PG call later)
            pay = Payment.objects.create(
                order=order,
                provider="stub",
                provider_order_id=f"stub_{order.id}",
                amount=total,
                status=Order.PaymentStatus.PENDING,
            )
            # Keep cart items until the webhook marks payment paid (idempotency-friendly)
            return Response(
                {
                    "detail": "Payment pending",
                    "order_id": order.id,
                    "pg_order_id": pay.provider_order_id,
                    "amount": str(total),
                },
                status=status.HTTP_201_CREATED,
            )

        # COD path: clear cart now
        cart_items.delete()
        return Response(
            {"detail": "Order placed successfully (COD)", "order_id": order.id},
            status=status.HTTP_201_CREATED,
        )


# ---------- PAYMENT WEBHOOK (STUB) ----------
class PaymentWebhookView(APIView):
    """
    Stub webhook endpoint. When you integrate a real gateway:
      - Verify signature
      - Lookup Payment by provider_order_id
      - On success: set Payment.status=PAID, order.payment_status=PAID, order.status=PLACED
      - On failure: mark payment/order failed and optionally restock
    """
    authentication_classes = []  # use HMAC or similar in real integration
    permission_classes = []

    def post(self, request):
        provider_order_id = request.data.get("provider_order_id")
        provider_payment_id = request.data.get("provider_payment_id", "")
        status_param = request.data.get("status", "PAID")  # pretend success by default

        if not provider_order_id:
            return Response({"detail": "provider_order_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pay = Payment.objects.select_related("order").get(provider_order_id=provider_order_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        order = pay.order

        if status_param == "PAID":
            pay.status = Order.PaymentStatus.PAID
            pay.provider_payment_id = provider_payment_id
            pay.save(update_fields=["status", "provider_payment_id"])

            order.payment_status = Order.PaymentStatus.PAID
            order.status = Order.Status.PLACED
            order.save(update_fields=["payment_status", "status"])

            # Clear cart if any remnants exist
            CartItem.objects.filter(user=order.user).delete()

            return Response({"detail": "Payment captured", "order_id": order.id}, status=status.HTTP_200_OK)

        # Failure branch
        pay.status = Order.PaymentStatus.FAILED
        pay.save(update_fields=["status"])

        order.payment_status = Order.PaymentStatus.FAILED
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["payment_status", "status"])

        # Optional: restock on failure (only if you decremented earlier and have stock field)
        # for oi in order.orderitem_set.select_related("product"):
        #     if hasattr(oi.product, "stock"):
        #         oi.product.__class__.objects.filter(pk=oi.product_id).update(stock=F("stock") + oi.quantity)

        return Response({"detail": "Payment failed", "order_id": order.id}, status=status.HTTP_400_BAD_REQUEST)
