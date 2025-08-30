# orders/admin.py
import csv
from django.contrib import admin
from django.http import HttpResponse
from .models import Order, OrderItem, Fulfillment


def export_csv(modeladmin, request, queryset):
    """Export selected orders to CSV with order items details"""
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename=orders.csv'
    w = csv.writer(resp)
    w.writerow(["order_id", "product", "qty", "supplier", "payment_method", "status"])
    
    for o in queryset.prefetch_related("items__product__supplier"):
        for it in o.items.all():
            w.writerow([
                o.id, 
                it.product.name, 
                it.quantity, 
                getattr(it.product.supplier, 'name', ""), 
                o.payment_method, 
                o.status
            ])
    return resp

export_csv.short_description = "Export to CSV"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "payment_method", "status", "ordered_at")
    list_filter = ("payment_method", "status")
    search_fields = ("id", "user__username")
    actions = [export_csv]  # Actions should be defined inside the class


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price", "total_price")
    list_filter = ("order__status", "product")
    search_fields = ("order__id", "product__name")


@admin.register(Fulfillment)
class FulfillmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "supplier", "status", "created_at", "updated_at")
    list_filter = ("status", "supplier")
    search_fields = ("external_ref", "tracking_number")