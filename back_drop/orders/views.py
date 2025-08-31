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
from .models import Order, OrderItem, Payment, Fulfillment, FulfillmentStatus
from .serializers import OrderSerializer
from cart.models import CartItem
from common.permissions import IsOwner
from dropship.models import Fulfillment
logger = logging.getLogger(__name__)

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
        payment_method = request.data.get("payment_method", Order.PaymentMethod.COD)

        # Load cart with related data
        cart_items = (CartItem.objects
                      .filter(user=user)
                      .select_related("product", "product__supplier"))
        
        if not cart_items.exists():
            return Response(
                {"detail": "Cart is empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Comprehensive validation
        validation_errors = self._validate_checkout(cart_items, payment_method, user)
        if validation_errors:
            return Response(
                {"detail": validation_errors[0]}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate totals
        subtotal = self._calculate_total(cart_items)

        # Check COD eligibility for all items
        all_cod_allowed = all(self._product_allows_cod(ci.product) for ci in cart_items)

        # Create order
        order = self._create_order(
            user=user,
            total=subtotal,
            payment_method=payment_method,
            cod_allowed=all_cod_allowed
        )

        # Create order items and fulfillments
        self._create_order_items_and_fulfillments(order, cart_items)

        # Update stock
        self._update_stock(cart_items)

        # Handle payment flow
        if payment_method == Order.PaymentMethod.COD:
            return self._handle_cod_payment(order, cart_items)
        else:
            return self._handle_online_payment(order, subtotal)

    def _validate_checkout(self, cart_items, payment_method, user):
        """Comprehensive checkout validation"""
        errors = []
        
        # Basic cart validation
        cart_errors = self._validate_cart_items(cart_items)
        if cart_errors:
            errors.extend(cart_errors)
        
        # Stock validation
        stock_error = self._validate_stock(cart_items)
        if stock_error:
            errors.append(stock_error)
        
        # COD validation
        if payment_method == Order.PaymentMethod.COD:
            cod_error = self._validate_cod_eligibility(cart_items, user)
            if cod_error:
                errors.append(cod_error)
        
        return errors

    def _product_allows_cod(self, product):
        """Check if a single product allows COD"""
        # Check product-level COD flags
        cod_available = getattr(product, "cod_available", True)
        cod_allowed = getattr(product, "cod_allowed", True)
        
        # Check supplier COD support
        supplier_ok = True
        if product.supplier:
            supplier_ok = getattr(product.supplier, "cod_supported", True)
        
        return bool(cod_available and cod_allowed and supplier_ok)

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
        # Check each product's COD eligibility
        for item in cart_items:
            if not self._product_allows_cod(item.product):
                return f"COD not available for {item.product.name}"
        
        # Check if user has valid address for COD
        if not self._user_has_valid_address(user):
            return "Please add a delivery address for COD orders"
            
        return None

    def _user_has_valid_address(self, user):
        """Check if user has a valid delivery address"""
        # TODO: Implement based on your user/address model
        # Example: return user.addresses.filter(is_default=True).exists()
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

    def _create_order(self, user, total, payment_method, cod_allowed):
        """Create the main order record"""
        return Order.objects.create(
            user=user,
            total_price=Decimal(total),
            payment_method=payment_method,
            payment_status=(
                Order.PaymentStatus.COD_PENDING 
                if payment_method == Order.PaymentMethod.COD
                else Order.PaymentStatus.PENDING
            ),
            status=(
                Order.Status.PLACED 
                if payment_method == Order.PaymentMethod.COD
                else Order.Status.PAYMENT_PENDING
            ),
            cod_allowed_snapshot=cod_allowed,
            customer_name=getattr(user, "get_full_name", lambda: user.username)(),
            customer_email=getattr(user, "email", ""),
        )

    def _create_order_items_and_fulfillments(self, order, cart_items):
        """Create order items and fulfillment records"""
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price,
                total_price=item.product.price * item.quantity,
            )
        
        # Create fulfillments grouped by supplier
        suppliers = {}
        for item in cart_items:
            supplier = item.product.supplier
            if not supplier:
                continue
            suppliers.setdefault(supplier.id, {
                "supplier": supplier, 
                "items": []
            })["items"].append(item)

        # Create fulfillment records for each supplier
        for supplier_data in suppliers.values():
            Fulfillment.objects.create(
                order=order, 
                supplier=supplier_data["supplier"], 
                status=(
                    "placed" if order.payment_method == Order.PaymentMethod.COD
                    else "pending"
                )
            )

    def _update_stock(self, cart_items):
        """Atomically update product stock"""
        for item in cart_items:
            if hasattr(item.product, "stock"):
                item.product.__class__.objects.filter(
                    pk=item.product.pk
                ).update(stock=F("stock") - item.quantity)

    def _handle_online_payment(self, order, total):
        """Handle online payment flow"""
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            provider="stub",  # Replace with real payment gateway
            provider_order_id=f"stub_{order.id}",
            amount=total,
            status=Order.PaymentStatus.PENDING,
        )
        
        return Response({
            "detail": "Payment pending",
            "order_id": order.id,
            "payment_id": payment.id,
            "pg_order_id": payment.provider_order_id,
            "amount": str(total),
            "status": order.status,
            "payment_status": order.payment_status,
        }, status=status.HTTP_201_CREATED)

    def _handle_cod_payment(self, order, cart_items):
        """Handle COD payment flow"""
        # Clear cart for successful COD orders
        cart_items.delete()
        
        return Response({
            "detail": "Order placed successfully (COD)",
            "order_id": order.id,
            "payment_method": order.payment_method,
            "total_price": str(order.total_price),
            "status": order.status,
            "payment_status": order.payment_status,
            "cod_allowed_snapshot": order.cod_allowed_snapshot,
        }, status=status.HTTP_201_CREATED)
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
            Fulfillment.objects.filter(
            order_item__order=order,
            status=FulfillmentStatus.PENDING
            ).update(status=FulfillmentStatus.PLACED)
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