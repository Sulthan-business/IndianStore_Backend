# dropship/models.py  (new app: `dropship`)
from django.db import models
from django.conf import settings
from products.models import Product
from orders.models import Order

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    supports_cod = models.BooleanField(default=True)
    lead_time_days = models.PositiveIntegerField(default=2)

    def __str__(self):
        return self.name


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
        related_name="dropship_fulfillments"   # ✅ different from above
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.CASCADE,
        related_name="dropship_fulfillments"   # ✅ different
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)

    # tracking
    carrier = models.CharField(max_length=100, blank=True)
    tracking_no = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # optional: snapshot minimal totals for supplier
    supplier_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Fulfillment #{self.id} for Order #{self.order_id} via {self.supplier}"
