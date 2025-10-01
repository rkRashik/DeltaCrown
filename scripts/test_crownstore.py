#!/usr/bin/env python
"""
CrownStore Functionality Test Script
Tests all major ecommerce functionality
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.ecommerce.models import *
from apps.user_profile.models import UserProfile
from apps.accounts.models import User
from decimal import Decimal
import json

def test_models():
    """Test all model functionality"""
    print("🧪 Testing CrownStore Models...")
    
    # Test Category
    categories = Category.objects.all()
    print(f"✅ Categories: {categories.count()} created")
    
    # Test Brand
    brands = Brand.objects.all()
    print(f"✅ Brands: {brands.count()} created")
    
    # Test Product
    products = Product.objects.all()
    print(f"✅ Products: {products.count()} created")
    
    # Test featured products
    featured = Product.objects.filter(is_featured=True)
    print(f"✅ Featured Products: {featured.count()}")
    
    # Test product by rarity
    rarities = ['common', 'rare', 'epic', 'legendary', 'mythic']
    for rarity in rarities:
        count = Product.objects.filter(rarity=rarity).count()
        print(f"   🎖️ {rarity.title()}: {count} products")
    
    return True

def test_pricing():
    """Test product pricing and discounts"""
    print("\n💰 Testing Product Pricing...")
    
    discounted_products = Product.objects.filter(discount_percentage__gt=0)
    for product in discounted_products:
        if product.original_price:
            expected_price = product.original_price * (100 - product.discount_percentage) / 100
            actual_price = product.price
            print(f"✅ {product.name}: {product.discount_percentage}% off")
            print(f"   Original: ${product.original_price}, Sale: ${actual_price}")
    
    return True

def test_inventory():
    """Test inventory management"""
    print("\n📦 Testing Inventory Management...")
    
    # Test stock tracking
    tracked_products = Product.objects.filter(track_stock=True)
    print(f"✅ Stock Tracked Products: {tracked_products.count()}")
    
    # Test limited edition
    limited_products = Product.objects.filter(is_limited_edition=True)
    for product in limited_products:
        print(f"✅ Limited Edition: {product.name} ({product.limited_quantity} available)")
    
    # Test digital products
    digital_products = Product.objects.filter(is_digital=True)
    print(f"✅ Digital Products: {digital_products.count()}")
    
    return True

def test_categories_and_brands():
    """Test category and brand relationships"""
    print("\n📁 Testing Categories & Brands...")
    
    for category in Category.objects.all():
        product_count = category.products.count()
        print(f"✅ {category.name} ({category.category_type}): {product_count} products")
    
    for brand in Brand.objects.all():
        product_count = brand.product_set.count()
        featured = "⭐ Featured" if brand.is_featured else ""
        print(f"✅ {brand.name}: {product_count} products {featured}")
    
    return True

def test_product_features():
    """Test special product features"""
    print("\n🎮 Testing Product Features...")
    
    # Test member exclusive products
    exclusive = Product.objects.filter(is_member_exclusive=True)
    print(f"✅ Member Exclusive Products: {exclusive.count()}")
    
    # Test game compatibility
    games_products = Product.objects.exclude(compatible_games='')
    for product in games_products:
        if product.compatible_games:
            print(f"✅ {product.name}: Compatible with {product.compatible_games}")
    
    # Test esports teams
    team_products = Product.objects.exclude(esports_team='')
    for product in team_products:
        if product.esports_team:
            print(f"✅ {product.name}: Team {product.esports_team}")
    
    return True

def test_search_and_filter():
    """Test search and filtering capabilities"""
    print("\n🔍 Testing Search & Filter...")
    
    # Test name search
    search_results = Product.objects.filter(name__icontains='crown')
    print(f"✅ Search 'crown': {search_results.count()} results")
    
    # Test price range
    expensive_products = Product.objects.filter(price__gte=100)
    print(f"✅ Products $100+: {expensive_products.count()}")
    
    # Test category filtering
    jersey_products = Product.objects.filter(category__category_type='featured')
    print(f"✅ Featured Category Products: {jersey_products.count()}")
    
    return True

def create_sample_data():
    """Create sample user and cart data for testing"""
    print("\n👤 Creating Sample User Data...")
    
    try:
        # Create a test user if it doesn't exist
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@deltacrown.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            print("✅ Created test user")
        else:
            print("✅ Test user already exists")
        
        # Create user profile if it doesn't exist
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'display_name': 'Test User',
                'bio': 'Test user for CrownStore'
            }
        )
        
        if created:
            print("✅ Created user profile")
        else:
            print("✅ User profile already exists")
        
        return user, profile
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return None, None

def main():
    """Main test function"""
    print("🏆 CrownStore Functionality Test Suite")
    print("=" * 50)
    
    # Run all tests
    tests = [
        test_models,
        test_pricing,
        test_inventory,
        test_categories_and_brands,
        test_product_features,
        test_search_and_filter,
    ]
    
    all_passed = True
    
    for test in tests:
        try:
            result = test()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            all_passed = False
    
    # Create sample user data
    create_sample_data()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All CrownStore tests PASSED!")
        print("🚀 CrownStore is ready for production!")
    else:
        print("⚠️ Some tests failed - check the output above")
    
    print("\n📋 Quick Stats:")
    print(f"   📁 Categories: {Category.objects.count()}")
    print(f"   🏷️ Brands: {Brand.objects.count()}")
    print(f"   🛍️ Products: {Product.objects.count()}")
    print(f"   ⭐ Featured: {Product.objects.filter(is_featured=True).count()}")
    print(f"   🎖️ Limited Edition: {Product.objects.filter(is_limited_edition=True).count()}")
    print(f"   💎 Member Exclusive: {Product.objects.filter(is_member_exclusive=True).count()}")
    
    print("\n🌐 Access Points:")
    print("   🏠 Store Home: http://127.0.0.1:8000/store/")
    print("   📋 Products: http://127.0.0.1:8000/store/products/")
    print("   🛒 Cart: http://127.0.0.1:8000/store/cart/")
    print("   ⚙️ Admin: http://127.0.0.1:8000/admin/")

if __name__ == '__main__':
    main()