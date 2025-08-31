from rest_framework import serializers
from .models import Order, OrderItem
from products.models import Product  # needed for product info
from cart.models import CartItem
from .models import Fulfillment
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user = serializers.ReadOnlyField(source='user.username')  # for frontend user display

    class Meta:
        model = Order
        fields = [
            "id", "user", "total_price",
            "payment_method", "payment_status", "status",
            "cod_allowed_snapshot",
            "customer_name", "customer_email",
            "ordered_at", "items"
        ]
        read_only_fields = ["user", "total_price", "payment_status", "status", "cod_allowed_snapshot", "ordered_at"]


    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        total = 0

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            unit_price = product.price  # get current price
            total_price = unit_price * quantity
            total += total_price

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )

        order.total_price = total
        order.save()
        return order


class FulfillmentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    class Meta:
        model = Fulfillment
        fields = ["id","supplier","supplier_name","status","tracking_no","created_at"]