# orders/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from products.models import Product
from decimal import Decimal


class Order(models.Model):
    class PaymentMethod(models.TextChoices):
        COD = "COD", "Cash on Delivery"
        ONLINE = "ONLINE", "Online"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        COD_PENDING = "COD_PENDING", "COD Pending"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PLACED = "PLACED", "Placed"
        CANCELLED = "CANCELLED", "Cancelled"
        FULFILLED = "FULFILLED", "Fulfilled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)

    cod_allowed_snapshot = models.BooleanField(default=False)
    ordered_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Order #{self.id} ({self.user.username})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=30)  # e.g. "razorpay"
    provider_order_id = models.CharField(max_length=100)
    provider_payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=Order.PaymentStatus.choices, default=Order.PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order #{self.order_id} - {self.status}"


class FulfillmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PLACED = "placed", "Placed with supplier"
    CONFIRMED = "confirmed", "Supplier confirmed"
    SHIPPED = "shipped", "Shipped"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed"


class Fulfillment(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        SENT = "SENT", "Sent to Supplier"
        ACCEPTED = "ACCEPTED", "Accepted by Supplier"
        SHIPPED = "SHIPPED", "Shipped"
        CANCELLED = "CANCELLED", "Cancelled"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="order_fulfillments",   # unique reverse name
        null=True, blank=True                # <- TEMPORARILY allow null
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="order_fulfillments"    # unique reverse name
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)

    carrier = models.CharField(max_length=100, blank=True)       # was external_ref
    tracking_no = models.CharField(max_length=100, blank=True)   # was tracking_number
    tracking_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    supplier_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Fulfillment #{self.id} for Order #{self.order_id} via {self.supplier}"
    

