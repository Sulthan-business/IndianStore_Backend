# orders/tests/test_checkout_payment.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from products.models import Product
from cart.models import CartItem
from orders.models import Order

User = get_user_model()

class CheckoutPaymentSmoke(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="a@a.com", password="pass123", username="a")
        self.client.force_authenticate(self.user)

    def test_cod_allowed(self):
        p = Product.objects.create(name="COD OK", price=10, stock=5, cod_available=True)
        CartItem.objects.create(user=self.user, product=p, quantity=2)
        r = self.client.post("/api/orders/checkout/", {"payment_method": "COD"}, format="json")
        self.assertEqual(r.status_code, 201)
        o = Order.objects.get(id=r.data["order_id"])
        self.assertEqual(o.payment_method, "COD")
        self.assertEqual(o.status, Order.Status.PLACED)
        self.assertEqual(o.payment_status, Order.PaymentStatus.COD_PENDING)

    def test_cod_blocked(self):
        p = Product.objects.create(name="No COD", price=10, stock=5, cod_available=False)
        CartItem.objects.create(user=self.user, product=p, quantity=1)
        r = self.client.post("/api/orders/checkout/", {"payment_method": "COD"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_online_stub(self):
        p = Product.objects.create(name="Online", price=15, stock=5, cod_available=False)
        CartItem.objects.create(user=self.user, product=p, quantity=1)
        r = self.client.post("/api/orders/checkout/", {"payment_method": "ONLINE"}, format="json")
        self.assertEqual(r.status_code, 201)
        o = Order.objects.get(id=r.data["order_id"])
        self.assertEqual(o.status, Order.Status.PAYMENT_PENDING)
