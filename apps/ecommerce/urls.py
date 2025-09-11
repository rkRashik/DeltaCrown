# apps/ecommerce/urls.py
from django.urls import path
from .views import product_list, checkout

app_name = "ecommerce"

urlpatterns = [
    path("", product_list, name="product_list"),
    path("checkout/", checkout, name="checkout"),
]

