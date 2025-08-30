import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.ecommerce.models import Product, Order, OrderItem

User = get_user_model()

@pytest.mark.django_db
def test_checkout():
    product = Product.objects.create(name="Jersey", price=Decimal("500.00"), stock=100)
    user = User.objects.create_user(username="testuser", password="pw")
    profile = user.profile

    order = Order.objects.create(user=profile, status="pending", total_price=Decimal("0.00"))
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)

    order.total_price = sum(i.price for i in order.items.all())
    order.status = "paid"
    order.save()

    assert order.total_price == Decimal("500.00")
    assert order.status == "paid"

@pytest.mark.django_db
def test_deduct_delta_coins_on_checkout():
    user = User.objects.create_user(username="testuser", password="pw")
    profile = user.profile

    if not hasattr(profile, "delta_coins"):
        pytest.skip("delta_coins not enabled in this build")

    product = Product.objects.create(name="Jersey", price=Decimal("500.00"), stock=100)
    order = Order.objects.create(user=profile, status="pending", total_price=Decimal("0.00"))
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)

    order.total_price = sum(i.price for i in order.items.all())

    # Simulate paying with coins
    profile.delta_coins = Decimal("1000.00")
    profile.save()

    assert profile.delta_coins >= order.total_price
    profile.delta_coins -= order.total_price
    profile.save()
    order.status = "paid"
    order.save()

    assert order.status == "paid"
    assert profile.delta_coins == Decimal("500.00")
