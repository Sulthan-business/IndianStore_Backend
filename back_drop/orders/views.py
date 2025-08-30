# orders/views.py
from decimal import Decimal
import logging
from collections import defaultdict
from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import ( extend_schema_view, extend_schema, OpenApiResponse, OpenApiExample)
from .models import Order, OrderItem, Payment
from .serializers import OrderSerializer
from cart.models import CartItem
from common.permissions import IsOwner
from dropship.models import Fulfillment
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
# Improved CheckoutView with fixes and enhancements

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
    ],
)
class CheckoutView(APIView):
    """
    Converts the authenticated user's cart into an order.
    Supports COD and ONLINE payment methods with comprehensive validation.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user

        # Lock user's cart rows for safe operations
        cart_items = (
            CartItem.objects
            .select_related("product", "product__supplier")
            .select_for_update()
            .filter(user=user)
        )

        if not cart_items.exists():
            return Response(
                {"detail": "Cart is empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate payment method
        method = (request.data.get("payment_method", "ONLINE")).upper()
        if method not in ("COD", "ONLINE"):
            return Response(
                {"detail": "Invalid payment_method. Use 'COD' or 'ONLINE'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate cart items
        validation_errors = self._validate_cart_items(cart_items)
        if validation_errors:
            return Response(
                {"detail": validation_errors[0]}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check COD eligibility
        if method == "COD":
            cod_error = self._validate_cod_eligibility(cart_items, user)
            if cod_error:
                return Response(
                    {"detail": cod_error}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Stock validation
        stock_error = self._validate_stock(cart_items)
        if stock_error:
            return Response(
                {"detail": stock_error}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate totals
        total = self._calculate_total(cart_items)
        
        # Create order
        order = self._create_order(user, total, method, cart_items)
        
        # Create order items and fulfillments
        self._create_order_items_and_fulfillments(order, cart_items)
        
        # Update stock
        self._update_stock(cart_items)

        # Handle payment flow
        if method == "ONLINE":
            return self._handle_online_payment(order, total)
        else:
            return self._handle_cod_payment(order, cart_items)

    def _validate_cart_items(self, cart_items):
        """Validate basic cart item requirements"""
        errors = []
        
        for item in cart_items:
            if item.quantity <= 0:
                errors.append(f"Invalid quantity for {item.product.name}")
            
            if not hasattr(item.product, 'price') or item.product.price <= 0:
                errors.append(f"Invalid price for {item.product.name}")
                
        return errors

    def _validate_cod_eligibility(self, cart_items, user):
        """Check if COD is available for all items and user"""
        # Check if all products allow COD
        for item in cart_items:
            if not getattr(item.product, "cod_available", False):
                return f"COD not available for {item.product.name}"
        
        # Check supplier COD support (standardize on 'supports_cod')
        for item in cart_items:
            supplier = getattr(item.product, 'supplier', None)
            if supplier and not getattr(supplier, "supports_cod", True):
                return f"Supplier doesn't support COD for {item.product.name}"
        
        # Optional: Check if user has valid address for COD
        if not self._user_has_valid_address(user):
            return "Please add a delivery address for COD orders"
            
        return None

    def _user_has_valid_address(self, user):
        """Check if user has a valid delivery address"""
        # Implement based on your user/address model
        return True  # Placeholder

    def _validate_stock(self, cart_items):
        """Validate stock availability"""
        for item in cart_items:
            if hasattr(item.product, "stock"):
                if item.product.stock < item.quantity:
                    return f"Insufficient stock for {item.product.name}. Available: {item.product.stock}"
        return None

    def _calculate_total(self, cart_items):
        """Calculate order total"""
        return sum(item.product.price * item.quantity for item in cart_items)

    def _create_order(self, user, total, method, cart_items):
        """Create the main order record"""
        cod_allowed = method == "COD"  # Already validated if method is COD
        
        return Order.objects.create(
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
            customer_name=getattr(user, "get_full_name", lambda: user.username)(),
            customer_email=getattr(user, "email", ""),
        )

    def _create_order_items_and_fulfillments(self, order, cart_items):
        """Create order items and fulfillment records"""
        supplier_totals = defaultdict(Decimal)
        suppliers = set()
        
        for item in cart_items:
            # Create order item
            order_item = OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
                total_price=item.product.price * item.quantity,
            )
            
            # Track supplier info
            supplier = getattr(item.product, "supplier", None)
            if supplier:
                suppliers.add(supplier)
                # Use dropship_cost if available, else unit_price
                cost_basis = (
                    getattr(item.product, 'dropship_cost', order_item.unit_price)
                    or order_item.unit_price
                )
                supplier_totals[supplier] += (cost_basis * order_item.quantity)

        # Create fulfillment records
        for supplier in suppliers:
            Fulfillment.objects.create(
                order=order,
                supplier=supplier,
                status=(
                    Fulfillment.Status.SENT if order.payment_method == "COD" 
                    else Fulfillment.Status.CREATED
                ),
                supplier_subtotal=supplier_totals[supplier],
            )

    def _update_stock(self, cart_items):
        """Atomically update product stock"""
        for item in cart_items:
            if hasattr(item.product, "stock"):
                item.product.__class__.objects.filter(
                    pk=item.product_id
                ).update(stock=F("stock") - item.quantity)

    def _handle_online_payment(self, order, total):
        """Handle online payment flow"""
        payment = Payment.objects.create(
            order=order,
            provider="stub",  # Replace with real provider
            provider_order_id=f"stub_{order.id}",
            amount=total,
            status=Order.PaymentStatus.PENDING,
        )
        
        return Response(
            {
                "detail": "Payment pending",
                "order_id": order.id,
                "pg_order_id": payment.provider_order_id,
                "amount": str(total),
            },
            status=status.HTTP_201_CREATED,
        )

    def _handle_cod_payment(self, order, cart_items):
        """Handle COD payment flow"""
        # Clear cart immediately for COD orders
        cart_items.delete()
        
        return Response(
            {
                "detail": "Order placed successfully (COD)", 
                "order_id": order.id
            },
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

            # Update fulfillments to SENT status after successful payment
            order.fulfillments.filter(status=Fulfillment.Status.CREATED).update(status=Fulfillment.Status.SENT)

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