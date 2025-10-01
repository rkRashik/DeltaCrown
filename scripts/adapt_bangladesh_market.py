#!/usr/bin/env python
"""
Update CrownStore prices for Bangladesh market
Converts USD prices to BDT (Bangladeshi Taka) with appropriate pricing for young gamers
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.ecommerce.models import Product
from decimal import Decimal

# USD to BDT conversion rate (approximate)
USD_TO_BDT = Decimal('110.00')

# Bangladesh-specific pricing adjustments for young gamers
def adjust_price_for_bd_market(usd_price):
    """
    Adjust pricing for Bangladesh market considering:
    - Lower purchasing power
    - Young gamer demographic
    - Competitive local pricing
    """
    bdt_price = usd_price * USD_TO_BDT
    
    # Apply Bangladesh market adjustment (make it more affordable)
    if bdt_price <= 1000:  # Small items
        adjusted_price = bdt_price * Decimal('0.6')  # 40% discount
    elif bdt_price <= 5000:  # Medium items
        adjusted_price = bdt_price * Decimal('0.7')  # 30% discount
    elif bdt_price <= 15000:  # Premium items
        adjusted_price = bdt_price * Decimal('0.75')  # 25% discount
    else:  # Luxury items
        adjusted_price = bdt_price * Decimal('0.8')  # 20% discount
    
    # Round to nearest 10 taka for cleaner pricing
    return (adjusted_price // 10) * 10

def update_product_prices():
    """Update all product prices for Bangladesh market"""
    print("🇧🇩 Updating CrownStore prices for Bangladesh market...")
    print("=" * 60)
    
    products = Product.objects.all()
    
    for product in products:
        old_price = product.price
        old_original = product.original_price
        
        # Update main price
        new_price = adjust_price_for_bd_market(old_price)
        product.price = new_price
        
        # Update original price if exists
        if old_original:
            new_original = adjust_price_for_bd_market(old_original)
            product.original_price = new_original
            
            # Recalculate discount percentage
            if new_original > new_price:
                discount = ((new_original - new_price) / new_original) * 100
                product.discount_percentage = int(discount)
        
        product.save()
        
        print(f"✅ {product.name}")
        print(f"   Price: ${old_price} → ৳{new_price}")
        if old_original:
            print(f"   Original: ${old_original} → ৳{product.original_price}")
            print(f"   Discount: {product.discount_percentage}%")
        print()

def create_sample_bd_products():
    """Create Bangladesh-specific sample products"""
    print("\n🎮 Creating Bangladesh-specific gaming products...")
    
    # Get categories and brands
    from apps.ecommerce.models import Category, Brand
    
    gaming_cat = Category.objects.get(slug='gaming-peripherals')
    esports_cat = Category.objects.get(slug='esports-jerseys')
    deltacrown_brand = Brand.objects.get(slug='deltacrown-official')
    
    bd_products = [
        {
            'name': 'DeltaCrown Gaming Mousepad - Bangladesh Edition',
            'slug': 'deltacrown-mousepad-bd-edition',
            'short_description': 'Premium gaming mousepad designed for Bangladeshi gamers',
            'description': 'High-quality gaming mousepad featuring Bangladesh-inspired designs. Perfect for PUBG Mobile, Free Fire, and other popular games in Bangladesh.',
            'price': Decimal('890'),  # ~$8 equivalent
            'original_price': Decimal('1200'),
            'discount_percentage': 26,
            'category': gaming_cat,
            'brand': deltacrown_brand,
            'rarity': 'rare',
            'stock': 200,
            'is_featured': True,
            'compatible_games': 'PUBG Mobile, Free Fire, Call of Duty Mobile',
            'esports_team': 'DeltaCrown BD'
        },
        {
            'name': 'BD Esports Jersey - Victory Edition',
            'slug': 'bd-esports-jersey-victory',
            'short_description': 'Comfortable jersey for Bangladeshi esports champions',
            'description': 'Lightweight, moisture-wicking jersey perfect for long gaming sessions. Features subtle Bangladesh-inspired color scheme.',
            'price': Decimal('1990'),  # ~$18 equivalent
            'original_price': Decimal('2500'),
            'discount_percentage': 20,
            'category': esports_cat,
            'brand': deltacrown_brand,
            'rarity': 'epic',
            'stock': 100,
            'is_featured': True,
            'compatible_games': 'All Esports Games',
            'esports_team': 'Bangladesh National Esports'
        },
        {
            'name': 'Student Gamer Bundle - Budget Edition',
            'slug': 'student-gamer-bundle-budget',
            'short_description': 'Affordable gaming accessories for student gamers',
            'description': 'Perfect starter pack for student gamers in Bangladesh. Includes essential gaming accessories at an affordable price.',
            'price': Decimal('2490'),  # ~$22 equivalent
            'original_price': Decimal('3500'),
            'discount_percentage': 29,
            'category': gaming_cat,
            'brand': deltacrown_brand,
            'rarity': 'common',
            'stock': 150,
            'is_featured': True,
            'compatible_games': 'Mobile Gaming, PC Gaming',
            'esports_team': 'Student Esports League'
        }
    ]
    
    for product_data in bd_products:
        product, created = Product.objects.get_or_create(
            slug=product_data['slug'],
            defaults=product_data
        )
        if created:
            print(f"✅ Created: {product.name} - ৳{product.price}")
        else:
            print(f"⚠️  Updated: {product.name} - ৳{product.price}")

def main():
    """Main function to update CrownStore for Bangladesh market"""
    print("🇧🇩 CROWNSTORE BANGLADESH MARKET ADAPTATION")
    print("=" * 60)
    print("Adapting CrownStore for young Bangladeshi gamers...")
    print("✨ Modern, affordable, and locally relevant")
    print()
    
    # Update existing product prices
    update_product_prices()
    
    # Create Bangladesh-specific products
    create_sample_bd_products()
    
    print("=" * 60)
    print("🎉 CrownStore successfully adapted for Bangladesh market!")
    print()
    print("💰 Pricing Summary:")
    print("   💸 Affordable for students and young gamers")
    print("   ৳ All prices in Bangladeshi Taka")
    print("   🎯 Competitive local market pricing")
    print()
    print("🎮 Product Focus:")
    print("   📱 Mobile gaming accessories (PUBG, Free Fire)")
    print("   🖥️  PC gaming peripherals")
    print("   👕 Comfortable esports apparel")
    print("   🎒 Student-friendly bundles")
    print()
    print("🚀 Ready for Bangladeshi gamers!")

if __name__ == '__main__':
    main()