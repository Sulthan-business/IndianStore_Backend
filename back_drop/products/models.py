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

    def __str__(self):
        return self.name
