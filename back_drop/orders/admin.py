from django.contrib import admin
from .models import Order, OrderItem, Fulfillment
# orders/admin.py
import csv
from django.http import HttpResponse


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "payment_method", "status", "ordered_at")
    list_filter = ("payment_method", "status")
    search_fields = ("id", "user__username")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price", "total_price")
    list_filter = ("order__status", "product")
    search_fields = ("order__id", "product__name")

@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order_item", "supplier", "status", "updated_at")
    list_filter = ("status", "supplier")
    search_fields = ("external_ref", "tracking_number")