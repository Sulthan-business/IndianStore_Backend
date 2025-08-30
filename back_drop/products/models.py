# products/models.py
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    cod_available = models.BooleanField(default=True)
    cod_allowed = models.BooleanField(default=True)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Reference to suppliers app
    supplier = models.ForeignKey(
        "suppliers.Supplier",  # Note: suppliers.Supplier, not products.Supplier
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products'
    )
    
    supplier_sku = models.CharField(max_length=100, blank=True)
    dropship_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    @property
    def is_cod_allowed(self):
        if not self.cod_allowed:
            return False
        if self.supplier and not self.supplier.cod_supported:
            return False
        return True