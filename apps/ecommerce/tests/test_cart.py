import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.ecommerce.models import Product, Order, OrderItem

User = get_user_model()

@pytest.mark.django_db
def test_add_to_cart():
    product = Product.objects.create(name="Jersey", price=Decimal("500.00"), stock=100)
    user = User.objects.create_user(username="testuser", password="pw")
    profile = user.profile  # created by signal

    # Ensure total_price default when creating pending order
    order, _ = Order.objects.get_or_create(
        user=profile, status="pending", defaults={"total_price": Decimal("0.00")}
    )

    item, _ = OrderItem.objects.get_or_create(
        order=order, product=product, defaults={"quantity": 0, "price": Decimal("0.00")}
    )
    item.quantity += 1
    item.price = product.price * item.quantity
    item.save()

    assert order.items.count() == 1
    assert item.quantity == 1
    assert item.price == Decimal("500.00")
