from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from products.models import Product, Supplier
from cart.models import CartItem

User = get_user_model()

class CODRuleTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        self.u = User.objects.create_user(username="u1", password="pass")
        self.c.force_authenticate(self.u)
        self.s = Supplier.objects.create(name="SupA")
        self.p1 = Product.objects.create(name="A", price=10, stock=5, cod_allowed=True, supplier=self.s)
        self.p2 = Product.objects.create(name="B", price=20, stock=5, cod_allowed=False, supplier=self.s)

    def test_cod_rejects_non_cod_items(self):
        CartItem.objects.create(user=self.u, product=self.p2, quantity=1)
        r = self.c.post("/api/orders/checkout/", {"payment_method":"COD"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("COD not available", r.data["detail"])

    def test_cod_ok_when_allowed(self):
        CartItem.objects.all().delete()
        CartItem.objects.create(user=self.u, product=self.p1, quantity=2)
        r = self.c.post("/api/orders/checkout/", {"payment_method":"COD"}, format="json")
        self.assertIn(r.status_code, (200,201))
