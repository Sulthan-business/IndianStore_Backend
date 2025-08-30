from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()

class CartSmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="cartuser", password="pass123")
        token = self.client.post(
            reverse("token_obtain_pair"), {"username": "cartuser", "password": "pass123"}, format="json"
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.product = Product.objects.create(name="Cart Prod", price=7.25)

    def test_add_and_summary(self):
        # add to cart
        r = self.client.post(reverse("cart-list-create"), {"product": self.product.id, "quantity": 2}, format="json")
        self.assertIn(r.status_code, (200, 201))

        # summary
        r = self.client.get(reverse("cart-summary"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["total_items"], 2)
