# suppliers/models.py  (new app if not created: `python manage.py startapp suppliers`)
from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True)
    cod_supported = models.BooleanField(default=True)  # supplier-level toggle

    def __str__(self): return self.name
