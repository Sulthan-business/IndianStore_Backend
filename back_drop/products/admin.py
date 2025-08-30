# products/admin.py
from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock", "cod_available")
    list_editable = ("price", "stock", "cod_available")
    search_fields = ("name",)
