import pytest
from apps.ecommerce.models import Product

@pytest.mark.django_db
def test_product_creation():
    product = Product.objects.create(name="Jersey", price=500, stock=100)
    assert product.name == "Jersey"
    assert product.price == 500
    assert product.stock == 100
