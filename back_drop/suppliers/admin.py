from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'cod_supported', 'is_active', 'lead_time_days']
    list_filter = ['cod_supported', 'is_active']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'updated_at']