# orders/tests/test_checkout_cod_rules.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import CustomUser
from products.models import Product
from suppliers.models import Supplier

class CheckoutCODRules(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.u = CustomUser.objects.create_user(username="u1", password="p1")
        r = self.c.post("/api/token/", {"username":"u1","password":"p1"}, format="json")
        self.c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.s = Supplier.objects.create(name="S1", cod_supported=True)
        self.p_cod = Product.objects.create(name="COD OK", price=100, stock=5, cod_allowed=True, supplier=self.s)
        self.p_no_cod = Product.objects.create(name="No COD", price=50, stock=5, cod_allowed=False, supplier=self.s)

    def test_cod_blocked_when_product_disallows(self):
        self.c.post("/api/cart/", {"product": self.p_no_cod.id, "quantity":1}, format="json")
        r = self.c.post("/api/orders/checkout/", {"payment_method":"COD"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cod_allowed_when_all_items_allow(self):
        self.c.post("/api/cart/", {"product": self.p_cod.id, "quantity":1}, format="json")
        r = self.c.post("/api/orders/checkout/", {"payment_method":"COD"}, format="json")
        self.assertIn(r.status_code, (200,201))
