from django.contrib import admin
from .models import Product



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'supplier', 'cod_allowed']
    list_filter = ['cod_allowed', 'supplier']
    search_fields = ['name', 'supplier__name']
