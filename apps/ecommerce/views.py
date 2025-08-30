from django.shortcuts import render, redirect
from .models import Product, Order, OrderItem
from apps.user_profile.models import UserProfile


def product_list(request):
    products = Product.objects.all()
    return render(request, "ecommerce/product_list.html", {"products": products})


def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    order, created = Order.objects.get_or_create(user=request.user.profile, status="pending")
    order_item, created = OrderItem.objects.get_or_create(order=order, product=product)

    order_item.quantity += 1  # Increase quantity by 1
    order_item.price = product.price * order_item.quantity
    order_item.save()

    return redirect("ecommerce:product_list")


def checkout(request):
    order = Order.objects.filter(user=request.user.profile, status="pending").first()
    if not order:
        return redirect("ecommerce:product_list")

    # Check if user has enough DeltaCrownCoins
    if request.user.profile.delta_coins >= order.total_price:
        request.user.profile.delta_coins -= order.total_price
        request.user.profile.save()

        order.status = "paid"
        order.save()
        # Send confirmation and complete the order
        return redirect("ecommerce:order_success", order_id=order.id)
    else:
        return render(request, "ecommerce/checkout.html", {"order": order, "error": "Insufficient DeltaCrownCoins"})
