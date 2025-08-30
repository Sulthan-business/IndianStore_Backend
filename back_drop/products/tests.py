from django.test import TestCase
from products.models import Product
from suppliers.models import Supplier  # if used

class ProductModelSmokeTests(TestCase):
    def test_create_product_without_supplier(self):
        p = Product.objects.create(
            name="Test Prod No Supplier",
            price=10.50,
            stock=5
        )
        self.assertGreater(p.id, 0)
        self.assertIsNone(p.supplier)
