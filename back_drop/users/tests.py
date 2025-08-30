from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthSmokeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.username = "smokeuser"
        self.email = "smoke@example.com"
        self.password = "smokepass123"

    def test_register_and_token(self):
        r = self.client.post("/api/users/register/", {
        "username": "test",
        "email": "test@example.com",
        "password": "pass1234"
    }, format="json")
        self.assertIn(r.status_code, (200, 201))
