# cart/serializers.py
from rest_framework import serializers
from .models import CartItem
from products.models import Product

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = CartItem
        fields = ['id', 'user', 'product', 'product_name', 'quantity', 'added_at']
        read_only_fields = ['id', 'added_at', 'user']
# cart/serializers.py (or wherever you create CartItem)
def validate_quantity(self, value):
    if value <= 0:
        raise serializers.ValidationError("Quantity must be > 0")
    return value
