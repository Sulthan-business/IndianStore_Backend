# orders/tests/test_checkout_smoke.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal

from products.models import Product
from cart.models import CartItem

# If Product.image is required, we generate a tiny in-memory PNG
# Safe even if image is optional.
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io


def make_image_file(name="test.png", size=(10, 10), color=(255, 0, 0)):
    file = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(file, format="PNG")
    file.seek(0)
    return SimpleUploadedFile(name, file.read(), content_type="image/png")


User = get_user_model()


class CheckoutSmokeTest(TestCase):
    """
    Minimal end-to-end check:
    - get JWT
    - create product (ORM)
    - add to cart (API)
    - checkout (API)
    - verify order created & cart cleared
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="smoke",
            email="smoke@example.com",
            password="pass1234",
        )

        # Create a product that satisfies required fields
        self.product = Product.objects.create(
            name="Test Product",
            price=Decimal("10.00"),
            image=make_image_file(),  # harmless if image is optional
        )

    def auth(self):
        """Obtain access token and set Authorization header."""
        r = self.client.post(
            "/api/token/", {"username": "smoke", "password": "pass1234"}, format="json"
        )
        self.assertEqual(r.status_code, 200, f"Token failed: {r.status_code} {r.content}")
        access = r.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_unauthenticated_checkout_is_401(self):
        r = self.client.post("/api/orders/checkout/", {}, format="json")
        self.assertIn(r.status_code, (401, 403))  # JWT required
        # Don’t fail the whole suite if it’s 403 in your config.

    def test_happy_path_checkout(self):
        self.auth()

        # Add item to cart
        r = self.client.post(
            "/api/cart/",
            {"product": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(r.status_code, 201, f"Cart add failed: {r.status_code} {r.content}")

        # Checkout
        r = self.client.post("/api/orders/checkout/", {}, format="json")
        self.assertEqual(r.status_code, 201, f"Checkout failed: {r.status_code} {r.content}")
        self.assertIn("order_id", r.data)

        # Cart should be empty now
        r = self.client.get("/api/cart/summary/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data.get("total_items"), 0)

        # Orders should list 1 order for this user
        r = self.client.get("/api/orders/my-orders/")
        # If your my-orders is GET-only and returns 200
        self.assertEqual(r.status_code, 200, f"My-orders failed: {r.status_code} {r.content}")
        self.assertGreaterEqual(len(r.data), 1)
