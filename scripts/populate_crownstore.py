#!/usr/bin/env python
"""
CrownStore Sample Data Population Script
Creates categories, brands, and products for the DeltaCrown ecommerce platform
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.ecommerce.models import Category, Brand, Product, ProductImage
from decimal import Decimal

def create_categories():
    """Create sample categories"""
    categories = [
        {
            'name': 'Esports Jerseys',
            'slug': 'esports-jerseys',
            'category_type': 'featured',
            'description': 'Official team jerseys and player replicas',
            'icon': 'fas fa-tshirt'
        },
        {
            'name': 'Gaming Peripherals',
            'slug': 'gaming-peripherals',
            'category_type': 'merchandise',
            'description': 'Professional gaming mice, keyboards, and headsets',
            'icon': 'fas fa-gamepad'
        },
        {
            'name': 'Crown Membership',
            'slug': 'crown-membership',
            'category_type': 'digital',
            'description': 'Premium subscriptions and digital perks',
            'icon': 'fas fa-crown'
        },
        {
            'name': 'Limited Edition',
            'slug': 'limited-edition',
            'category_type': 'limited',
            'description': 'Exclusive limited-time collections',
            'icon': 'fas fa-gem'
        },
        {
            'name': 'Team Merchandise',
            'slug': 'team-merchandise',
            'category_type': 'merchandise',
            'description': 'Official team logos and accessories',
            'icon': 'fas fa-users'
        }
    ]
    
    created_cats = []
    for cat_data in categories:
        category, created = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        created_cats.append(category)
        print(f"{'Created' if created else 'Updated'} category: {category.name}")
    
    return created_cats

def create_brands():
    """Create sample brands"""
    brands = [
        {
            'name': 'DeltaCrown Official',
            'slug': 'deltacrown-official',
            'description': 'Official DeltaCrown branded merchandise',
            'is_featured': True
        },
        {
            'name': 'Valorant Pro',
            'slug': 'valorant-pro',
            'description': 'Professional Valorant team gear',
            'is_featured': True
        },
        {
            'name': 'eFootball Elite',
            'slug': 'efootball-elite',
            'description': 'Elite eFootball team collections',
            'is_featured': True
        },
        {
            'name': 'Gaming Gear Co',
            'slug': 'gaming-gear-co',
            'description': 'Professional gaming peripherals',
            'is_featured': False
        }
    ]
    
    created_brands = []
    for brand_data in brands:
        brand, created = Brand.objects.get_or_create(
            slug=brand_data['slug'],
            defaults=brand_data
        )
        created_brands.append(brand)
        print(f"{'Created' if created else 'Updated'} brand: {brand.name}")
    
    return created_brands

def create_products(categories, brands):
    """Create sample products"""
    products = [
        # Featured Esports Jerseys
        {
            'name': 'DeltaCrown Official Jersey 2024',
            'slug': 'deltacrown-official-jersey-2024',
            'short_description': 'Official DeltaCrown team jersey with premium fabric',
            'description': 'Premium quality esports jersey featuring the iconic DeltaCrown logo. Made with moisture-wicking fabric for maximum comfort during intense gaming sessions.',
            'price': Decimal('89.99'),
            'original_price': Decimal('119.99'),
            'discount_percentage': 25,
            'category': categories[0],  # Esports Jerseys
            'brand': brands[0],  # DeltaCrown Official
            'rarity': 'legendary',
            'stock': 50,
            'is_featured': True,
            'compatible_games': 'Valorant, eFootball, CS:GO',
            'esports_team': 'DeltaCrown Pro'
        },
        {
            'name': 'Valorant Champions Jersey',
            'slug': 'valorant-champions-jersey',
            'short_description': 'Limited edition Valorant championship jersey',
            'description': 'Celebrate victory with this limited edition championship jersey. Features holographic elements and premium stitching.',
            'price': Decimal('149.99'),
            'original_price': Decimal('199.99'),
            'discount_percentage': 25,
            'category': categories[0],  # Esports Jerseys
            'brand': brands[1],  # Valorant Pro
            'rarity': 'mythic',
            'stock': 25,
            'is_featured': True,
            'is_limited_edition': True,
            'limited_quantity': 100,
            'compatible_games': 'Valorant',
            'esports_team': 'Valorant Champions'
        },
        
        # Gaming Peripherals
        {
            'name': 'Crown Gaming Mouse Pro',
            'slug': 'crown-gaming-mouse-pro',
            'short_description': 'Professional gaming mouse with RGB lighting',
            'description': 'High-precision gaming mouse with 16000 DPI, customizable RGB lighting, and ergonomic design for professional esports players.',
            'price': Decimal('79.99'),
            'original_price': Decimal('99.99'),
            'discount_percentage': 20,
            'category': categories[1],  # Gaming Peripherals
            'brand': brands[3],  # Gaming Gear Co
            'rarity': 'epic',
            'stock': 100,
            'is_featured': True,
            'compatible_games': 'All Games'
        },
        {
            'name': 'Elite Mechanical Keyboard',
            'slug': 'elite-mechanical-keyboard',
            'short_description': 'Professional mechanical keyboard with crown switches',
            'description': 'Tournament-grade mechanical keyboard featuring custom Crown switches, per-key RGB lighting, and aluminum frame.',
            'price': Decimal('159.99'),
            'original_price': Decimal('199.99'),
            'discount_percentage': 20,
            'category': categories[1],  # Gaming Peripherals
            'brand': brands[3],  # Gaming Gear Co
            'rarity': 'legendary',
            'stock': 75,
            'is_featured': True,
            'compatible_games': 'All Games'
        },
        
        # Digital Products
        {
            'name': 'Crown Premium Membership',
            'slug': 'crown-premium-membership',
            'short_description': 'Monthly premium membership with exclusive perks',
            'description': 'Access exclusive tournaments, premium coaching, priority matchmaking, and member-only merchandise discounts.',
            'price': Decimal('19.99'),
            'category': categories[2],  # Crown Membership
            'brand': brands[0],  # DeltaCrown Official
            'rarity': 'epic',
            'product_type': 'subscription',
            'is_digital': True,
            'is_member_exclusive': True,
            'stock': 999,
            'track_stock': False
        },
        {
            'name': 'DeltaCrown Coins Pack',
            'slug': 'deltacrown-coins-pack',
            'short_description': '1000 DeltaCrown Coins for store purchases',
            'description': 'Digital currency pack for CrownStore purchases. Coins never expire and can be used for any store item.',
            'price': Decimal('9.99'),
            'category': categories[2],  # Crown Membership
            'brand': brands[0],  # DeltaCrown Official
            'rarity': 'common',
            'product_type': 'digital',
            'is_digital': True,
            'stock': 999,
            'track_stock': False
        },
        
        # Limited Edition Items
        {
            'name': 'Golden Crown Collectible',
            'slug': 'golden-crown-collectible',
            'short_description': 'Limited edition golden crown statue',
            'description': 'Handcrafted golden crown statue with certificate of authenticity. Only 50 pieces available worldwide.',
            'price': Decimal('499.99'),
            'category': categories[3],  # Limited Edition
            'brand': brands[0],  # DeltaCrown Official
            'rarity': 'mythic',
            'stock': 50,
            'is_featured': True,
            'is_limited_edition': True,
            'limited_quantity': 50,
            'is_member_exclusive': True
        },
        
        # Team Merchandise
        {
            'name': 'Team Logo Hoodie',
            'slug': 'team-logo-hoodie',
            'short_description': 'Comfortable hoodie with embroidered team logo',
            'description': 'Premium cotton blend hoodie featuring embroidered team logos. Available in multiple team designs.',
            'price': Decimal('59.99'),
            'original_price': Decimal('79.99'),
            'discount_percentage': 25,
            'category': categories[4],  # Team Merchandise
            'brand': brands[0],  # DeltaCrown Official
            'rarity': 'rare',
            'stock': 150,
            'compatible_games': 'All Teams'
        }
    ]
    
    created_products = []
    for product_data in products:
        product, created = Product.objects.get_or_create(
            slug=product_data['slug'],
            defaults=product_data
        )
        created_products.append(product)
        print(f"{'Created' if created else 'Updated'} product: {product.name}")
    
    return created_products

def main():
    """Main function to populate the CrownStore"""
    print("🏆 Populating CrownStore with sample data...")
    print("=" * 50)
    
    # Create categories
    print("\n📁 Creating Categories...")
    categories = create_categories()
    
    # Create brands
    print("\n🏷️ Creating Brands...")
    brands = create_brands()
    
    # Create products
    print("\n🛍️ Creating Products...")
    products = create_products(categories, brands)
    
    print("\n" + "=" * 50)
    print(f"✅ CrownStore populated successfully!")
    print(f"📊 Created {len(categories)} categories, {len(brands)} brands, and {len(products)} products")
    print("\n🚀 Ready to launch CrownStore!")
    print("💡 Access the admin panel to manage products: /admin/")
    print("🛒 Visit the store: /store/")

if __name__ == '__main__':
    main()