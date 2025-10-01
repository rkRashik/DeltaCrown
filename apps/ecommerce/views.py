from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    Product, Category, Brand, Cart, CartItem, Order, OrderItem, 
    Wishlist, Review, Coupon, LoyaltyProgram, ProductVariant
)
from apps.user_profile.models import UserProfile


def store_home(request):
    """CrownStore homepage with featured collections"""
    # Featured products
    featured_products = Product.objects.filter(
        is_featured=True, is_active=True
    ).select_related('category', 'brand')[:8]
    
    # Categories
    categories = Category.objects.filter(is_active=True).order_by('sort_order')
    
    # Limited edition products
    limited_products = Product.objects.filter(
        is_limited_edition=True, is_active=True
    ).select_related('category', 'brand')[:6]
    
    # Latest products
    latest_products = Product.objects.filter(
        is_active=True
    ).select_related('category', 'brand').order_by('-created_at')[:8]
    
    # Member exclusive products
    member_exclusive = Product.objects.filter(
        is_member_exclusive=True, is_active=True
    ).select_related('category', 'brand')[:4]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'limited_products': limited_products,
        'latest_products': latest_products,
        'member_exclusive': member_exclusive,
        'page_title': 'CrownStore - Premium Esports Marketplace',
    }
    return render(request, "ecommerce/store_home.html", context)


def product_list(request):
    """Product listing with filters and search"""
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand'
    ).prefetch_related('images')
    
    # Search functionality
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query)
        )
    
    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Brand filter
    brand_slug = request.GET.get('brand')
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Product type filter
    product_type = request.GET.get('type')
    if product_type:
        products = products.filter(product_type=product_type)
    
    # Rarity filter
    rarity = request.GET.get('rarity')
    if rarity:
        products = products.filter(rarity=rarity)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options for sidebar
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'query': query,
        'current_filters': {
            'category': category_slug,
            'brand': brand_slug,
            'min_price': min_price,
            'max_price': max_price,
            'type': product_type,
            'rarity': rarity,
            'sort': sort_by,
        },
        'page_title': 'All Products - CrownStore',
    }
    return render(request, "ecommerce/product_list.html", context)


def category_detail(request, slug):
    """Category page with products"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(
        category=category, is_active=True
    ).select_related('brand').prefetch_related('images')
    
    # Apply same filters as product_list
    query = request.GET.get('q', '')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'query': query,
        'sort_by': sort_by,
        'page_title': f'{category.name} - CrownStore',
    }
    return render(request, "ecommerce/category_detail.html", context)


def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related(
            'images', 'variants', 'reviews__user'
        ),
        slug=slug, is_active=True
    )
    
    # Related products
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id).select_related('category', 'brand')[:4]
    
    # Reviews
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    rating_counts = {i: reviews.filter(rating=i).count() for i in range(1, 6)}
    
    # Check if user has this in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user.profile)
        in_wishlist = wishlist.products.filter(id=product.id).exists()
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews[:10],  # Show first 10 reviews
        'avg_rating': round(avg_rating, 1),
        'rating_counts': rating_counts,
        'total_reviews': reviews.count(),
        'in_wishlist': in_wishlist,
        'page_title': f'{product.name} - CrownStore',
    }
    return render(request, "ecommerce/product_detail.html", context)


@login_required
@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    """Add product to cart via AJAX"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Check stock
        if not product.is_in_stock:
            return JsonResponse({
                'success': False,
                'message': 'Product is out of stock'
            })
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user.profile)
        
        # Get variant if specified
        variant_id = request.POST.get('variant_id')
        variant = None
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        
        # Get quantity
        quantity = int(request.POST.get('quantity', 1))
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_total': cart.total_items
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
def cart_view(request):
    """Shopping cart page"""
    try:
        cart = Cart.objects.get(user=request.user.profile)
        cart_items = cart.items.select_related('product', 'variant').all()
    except Cart.DoesNotExist:
        cart_items = []
        cart = None
    
    context = {
        'cart_items': cart_items,
        'cart': cart,
        'page_title': 'Shopping Cart - CrownStore',
    }
    return render(request, "ecommerce/cart.html", context)


@login_required
@require_http_methods(["POST"])
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        cart_item = get_object_or_404(
            CartItem, 
            id=item_id, 
            cart__user=request.user.profile
        )
        
        action = request.POST.get('action')
        
        if action == 'increase':
            cart_item.quantity += 1
        elif action == 'decrease':
            cart_item.quantity = max(1, cart_item.quantity - 1)
        elif action == 'remove':
            cart_item.delete()
            return JsonResponse({'success': True, 'removed': True})
        else:
            quantity = int(request.POST.get('quantity', 1))
            cart_item.quantity = max(1, quantity)
        
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'quantity': cart_item.quantity,
            'item_total': float(cart_item.total_price),
            'cart_total': float(cart_item.cart.total_price)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def checkout(request):
    """Checkout process"""
    try:
        cart = Cart.objects.get(user=request.user.profile)
        if not cart.items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('ecommerce:cart')
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect('ecommerce:store_home')
    
    if request.method == 'POST':
        return process_checkout(request, cart)
    
    # Calculate totals
    subtotal = cart.total_price
    tax_amount = subtotal * Decimal('0.08')  # 8% tax
    shipping_cost = Decimal('0.00') if any(item.product.is_digital for item in cart.items.all()) else Decimal('9.99')
    total = subtotal + tax_amount + shipping_cost
    
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'shipping_cost': shipping_cost,
        'total': total,
        'page_title': 'Checkout - CrownStore',
    }
    return render(request, "ecommerce/checkout.html", context)


def process_checkout(request, cart):
    """Process the checkout form"""
    try:
        # Get form data
        billing_name = request.POST.get('billing_name')
        billing_email = request.POST.get('billing_email')
        billing_phone = request.POST.get('billing_phone', '')
        billing_address = request.POST.get('billing_address')
        billing_city = request.POST.get('billing_city')
        billing_state = request.POST.get('billing_state')
        billing_zip = request.POST.get('billing_zip')
        billing_country = request.POST.get('billing_country')
        
        payment_method = request.POST.get('payment_method', 'delta_coins')
        
        # Calculate totals
        subtotal = cart.total_price
        tax_amount = subtotal * Decimal('0.08')
        shipping_cost = Decimal('0.00') if any(item.product.is_digital for item in cart.items.all()) else Decimal('9.99')
        total = subtotal + tax_amount + shipping_cost
        
        # Check payment method
        if payment_method == 'delta_coins':
            if request.user.profile.delta_coins < total:
                messages.error(request, "Insufficient DeltaCrown Coins.")
                return redirect('ecommerce:checkout')
        
        # Create order
        order = Order.objects.create(
            user=request.user.profile,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            total_price=total,
            payment_method=payment_method,
            billing_name=billing_name,
            billing_email=billing_email,
            billing_phone=billing_phone,
            billing_address=billing_address,
            billing_city=billing_city,
            billing_state=billing_state,
            billing_zip=billing_zip,
            billing_country=billing_country,
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price,
                product_name=cart_item.product.name,
                product_sku=cart_item.variant.sku if cart_item.variant else cart_item.product.slug,
            )
            
            # Update stock
            if cart_item.product.track_stock:
                if cart_item.variant:
                    cart_item.variant.stock = F('stock') - cart_item.quantity
                    cart_item.variant.save()
                else:
                    cart_item.product.stock = F('stock') - cart_item.quantity
                    cart_item.product.save()
        
        # Process payment
        if payment_method == 'delta_coins':
            request.user.profile.delta_coins = F('delta_coins') - total
            request.user.profile.save()
            order.status = 'paid'
            order.save()
        
        # Clear cart
        cart.items.all().delete()
        
        # Update loyalty points
        loyalty, created = LoyaltyProgram.objects.get_or_create(user=request.user.profile)
        loyalty.points = F('points') + int(total)
        loyalty.total_spent = F('total_spent') + total
        loyalty.save()
        
        messages.success(request, f"Order #{order.order_number} placed successfully!")
        return redirect('ecommerce:order_success', order_number=order.order_number)
        
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('ecommerce:checkout')


def order_success(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Ensure user can only view their own orders
    if request.user.is_authenticated and order.user != request.user.profile:
        raise Http404()
    
    context = {
        'order': order,
        'page_title': 'Order Confirmation - CrownStore',
    }
    return render(request, "ecommerce/order_success.html", context)


@login_required
def order_detail(request, order_number):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user.profile
    )
    
    context = {
        'order': order,
        'page_title': f'Order #{order.order_number} - CrownStore',
    }
    return render(request, "ecommerce/order_detail.html", context)


@login_required
def wishlist_view(request):
    """Wishlist page"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user.profile)
    products = wishlist.products.filter(is_active=True).select_related('category', 'brand')
    
    context = {
        'wishlist_products': products,
        'page_title': 'My Wishlist - CrownStore',
    }
    return render(request, "ecommerce/wishlist.html", context)


@login_required
@require_http_methods(["POST"])
def toggle_wishlist(request, product_id):
    """Add/remove product from wishlist"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user.profile)
        
        if wishlist.products.filter(id=product_id).exists():
            wishlist.products.remove(product)
            in_wishlist = False
            message = f"{product.name} removed from wishlist"
        else:
            wishlist.products.add(product)
            in_wishlist = True
            message = f"{product.name} added to wishlist"
        
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# API endpoints for frontend
@require_http_methods(["GET"])
def search_products(request):
    """Search products API endpoint"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'products': []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(short_description__icontains=query),
        is_active=True
    ).select_related('category')[:10]
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': float(product.price),
            'image': product.featured_image.url if product.featured_image else None,
            'category': product.category.name,
        })
    
    return JsonResponse({'products': results})


@require_http_methods(["POST"])
def validate_coupon(request):
    """Validate coupon code"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please log in'})
    
    code = request.POST.get('code', '').upper()
    if not code:
        return JsonResponse({'success': False, 'message': 'Please enter a coupon code'})
    
    try:
        coupon = Coupon.objects.get(code=code)
        
        if not coupon.is_valid:
            return JsonResponse({'success': False, 'message': 'Coupon is not valid or expired'})
        
        if coupon.member_exclusive and not hasattr(request.user.profile, 'loyalty_program'):
            return JsonResponse({'success': False, 'message': 'This coupon is for members only'})
        
        # Calculate discount (you'd need cart total for this)
        return JsonResponse({
            'success': True,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'description': coupon.description
        })
        
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code'})
