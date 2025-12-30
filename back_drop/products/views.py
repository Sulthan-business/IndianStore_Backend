from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "name"]
    ordering = ["-id"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
   # Temporary fix to get the schema working:
    # INC.  ORRECT CODE
    filterset_fields = []
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at"]