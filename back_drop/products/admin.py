# products/admin.py
from django.contrib import admin
from .models import Product,Supplier

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "stock", "cod_available", "supplier")
    list_editable = ("price", "stock", "cod_available")
    list_filter = ("cod_available", "supplier")
    search_fields = ("name",)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "cod_supported", "is_active", "lead_time_days")
    search_fields = ("name", "email", "phone")
    list_filter = ("cod_supported", "is_active")
