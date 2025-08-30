from django.test import TestCase
from .models import Product

class ProductModelSmokeTests(TestCase):
    def test_create_product(self):
        p = Product.objects.create(
            name="Test Prod",
            price=10.50,
            stock=5  # now required
        )
        self.assertGreater(p.id, 0)
