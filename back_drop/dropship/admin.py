# dropship/admin.py
from django.contrib import admin
from .models import Supplier, Fulfillment

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "supports_cod", "lead_time_days", "email")
    list_filter = ("supports_cod",)
    search_fields = ("name", "email")

@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "supplier", "status", "carrier", "tracking_no", "created_at")
    list_filter = ("status", "supplier")
    search_fields = ("tracking_no", "order__id")
