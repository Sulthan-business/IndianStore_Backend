# products/models.py
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)  # ✅ unified (200 vs 255 → using 255 is safer)
    description = models.TextField(blank=True, null=True)  # ✅ from first version
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)  # ✅ use PositiveIntegerField
    cod_available = models.BooleanField(default=True)  # ✅ from second version
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)  # ✅ from first version
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ from first version

 # NEW dropship fields:
    supplier = models.ForeignKey("dropship.Supplier", on_delete=models.PROTECT, null=True, blank=True)
    supplier_sku = models.CharField(max_length=100, blank=True)
    dropship_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # optional for margin

    def __str__(self):
        return self.name
class Supplier(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    cod_supported = models.BooleanField(default=True)
    api_endpoint = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    lead_time_days = models.PositiveIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # products/models.py – add FK
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name
    # ---- augment your existing Product model (add these fields) ----
# inside class Product(models.Model): add the following fields
# (if they don't already exist)

    # which supplier ships this product (optional)
    supplier = models.ForeignKey(
        'products.Supplier',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='products'
    )
    
    supplier_sku = models.CharField(max_length=100, blank=True)
    cod_allowed = models.BooleanField(default=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)