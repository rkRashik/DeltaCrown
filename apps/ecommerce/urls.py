# apps/ecommerce/urls.py
from django.urls import path
from . import views

app_name = "ecommerce"

urlpatterns = [
    # Main store pages
    path("", views.store_home, name="store_home"),
    path("products/", views.product_list, name="product_list"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    
    # Cart management
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    
    # Checkout and orders
    path("checkout/", views.checkout, name="checkout"),
    path("order/success/<str:order_number>/", views.order_success, name="order_success"),
    path("order/<str:order_number>/", views.order_detail, name="order_detail"),
    
    # Wishlist
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    
    # API endpoints
    path("api/search/", views.search_products, name="search_products"),
    path("api/coupon/validate/", views.validate_coupon, name="validate_coupon"),
]

