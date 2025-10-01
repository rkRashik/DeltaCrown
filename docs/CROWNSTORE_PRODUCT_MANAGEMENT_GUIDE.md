# 🛍️ CrownStore Product Management Guide

## 📋 Table of Contents
1. [Getting Started](#getting-started)
2. [Adding New Products](#adding-new-products)
3. [Managing Categories & Brands](#managing-categories--brands)
4. [Price Management](#price-management)
5. [Inventory Tracking](#inventory-tracking)
6. [Bangladesh Market Features](#bangladesh-market-features)
7. [Image Management](#image-management)
8. [SEO & Marketing](#seo--marketing)
9. [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### Admin Access
1. **Access Admin Panel**: http://127.0.0.1:8000/admin/
2. **Login Credentials**: Use your Django superuser account
3. **Navigate to Ecommerce Section**: Look for "ECOMMERCE" section in admin

### Quick Setup Checklist
- [ ] Django server running
- [ ] Database migrated
- [ ] Sample data populated
- [ ] Admin user created
- [ ] Static files collected

---

## 🛒 Adding New Products

### Step 1: Basic Product Information

#### Required Fields:
- **Name**: Product title (e.g., "Gaming Mouse Pro Max")
- **Slug**: URL-friendly name (auto-generated from name)
- **Description**: Full product description
- **Short Description**: Brief summary for cards
- **Price**: Current selling price in BDT
- **Category**: Select appropriate category
- **Stock**: Available quantity

#### Example Product Setup:
```
Name: "DeltaCrown Gaming Headset - BD Edition"
Slug: "deltacrown-gaming-headset-bd-edition"
Price: ৳2490 (enter as 2490)
Category: "Gaming Peripherals"
Stock: 50
```

### Step 2: Bangladesh-Specific Settings

#### Pricing Strategy:
- **Budget Range**: ৳500 - ৳1,500 (Student-friendly)
- **Mid Range**: ৳1,500 - ৳3,500 (Enthusiast)
- **Premium**: ৳3,500 - ৳8,000 (Pro gamer)
- **Luxury**: ৳8,000+ (Elite gear)

#### Market Categories:
- **Physical Products**: Gaming peripherals, apparel
- **Digital Products**: Game credits, memberships
- **Subscriptions**: Monthly gaming services
- **Bundles**: Combo packages for students

### Step 3: Product Features

#### Rarity System:
- **Common** (Gray): Basic items, everyday gear
- **Rare** (Blue): Quality items, branded products
- **Epic** (Purple): High-end gear, limited availability
- **Legendary** (Orange): Premium products, pro-level
- **Mythic** (Red): Ultra-rare, exclusive items

#### Special Flags:
- **Is Featured**: Shows on homepage
- **Is Digital**: No shipping required
- **Is Member Exclusive**: Premium users only
- **Is Limited Edition**: Time/quantity limited
- **Track Stock**: Enable inventory management

### Step 4: Bangladesh Gaming Context

#### Compatible Games (Popular in BD):
- **Mobile**: PUBG Mobile, Call of Duty Mobile, Free Fire
- **PC**: Valorant, CS:GO, Dota 2, FIFA
- **Console**: FIFA, Call of Duty, Forza

#### Esports Teams:
- "Bangladesh National Esports"
- "DeltaCrown Pro Team"
- "University Esports League"
- "Mobile Gaming Champions"

---

## 📁 Managing Categories & Brands

### Category Types:
1. **Featured Collections**: Hero products, main attractions
2. **Esports Lifestyle**: Apparel, accessories, lifestyle
3. **Subscriptions & Utilities**: Digital services, memberships
4. **Member Exclusive**: VIP-only products
5. **Limited Edition**: Time-sensitive collections

### Creating New Category:
```
Name: "Mobile Gaming Accessories"
Slug: "mobile-gaming-accessories"
Type: "merchandise"
Description: "Essential accessories for mobile gaming champions"
Icon: "fas fa-mobile-alt"
```

### Brand Management:
```
Popular Gaming Brands in Bangladesh:
- DeltaCrown Official (Local brand)
- Razer (International)
- Logitech (Affordable range)
- SteelSeries (Mid-range)
- HyperX (Budget-friendly)
```

---

## 💰 Price Management

### Bangladesh Pricing Strategy

#### Currency Conversion:
- Use the provided script: `python scripts/adapt_bangladesh_market.py`
- Manual conversion: USD × 110 × (0.6-0.8 adjustment factor)

#### Price Examples:
```
Gaming Mouse:
- USD: $25
- BDT Direct: ৳2,750
- BD Adjusted: ৳1,990 (28% discount for local market)

Gaming Keyboard:
- USD: $60
- BDT Direct: ৳6,600
- BD Adjusted: ৳4,490 (32% discount for students)
```

#### Discount Strategy:
- **Student Discount**: 20-40% off regular prices
- **Bundle Deals**: Buy 2 get 15% off
- **Seasonal Sales**: Eid, Victory Day, New Year
- **Flash Sales**: Limited time offers

### Setting Prices in Admin:
1. Go to **Products** in admin
2. Edit existing product or add new
3. Set **Price** in BDT (no currency symbol needed)
4. Set **Original Price** if on sale
5. **Discount Percentage** auto-calculates

---

## 📦 Inventory Tracking

### Stock Management:
- **Track Stock**: Enable for physical products
- **Allow Backorder**: Let customers order out-of-stock items
- **Low Stock Alert**: Automatic warnings at 5 items
- **Reorder Level**: Set minimum stock thresholds

### Stock Status Display:
- **In Stock**: Green checkmark
- **Low Stock**: Orange warning (≤5 items)
- **Out of Stock**: Red X mark
- **Unlimited**: Digital products, subscriptions

### Inventory Reports:
```sql
-- View low stock products
SELECT name, stock FROM ecommerce_product 
WHERE stock <= 5 AND track_stock = true;

-- View best sellers
SELECT name, COUNT(*) as sales FROM ecommerce_product p
JOIN ecommerce_orderitem oi ON p.id = oi.product_id
GROUP BY p.name ORDER BY sales DESC;
```

---

## 🇧🇩 Bangladesh Market Features

### Payment Methods:
- **bKash**: Most popular mobile payment
- **Nagad**: Government-backed mobile payment
- **Rocket**: DBBL mobile payment
- **Bank Transfer**: Traditional method
- **Cash on Delivery**: For trust building

### Shipping Zones:
- **Dhaka Metro**: Same day delivery
- **Major Cities**: 1-2 days (Chittagong, Sylhet, Khulna)
- **Other Areas**: 3-5 days
- **Remote Areas**: 5-7 days

### Local Holidays:
- **Eid ul-Fitr**: Major shopping season
- **Eid ul-Adha**: Gift-giving period
- **Victory Day** (Dec 16): Patriotic themes
- **Independence Day** (Mar 26): National pride
- **Durga Puja**: Electronics sales boost

### Student Market:
- **University Areas**: High demand zones
- **Budget Focus**: ৳500-2000 sweet spot
- **Exam Seasons**: Lower activity
- **Result Seasons**: Reward purchases

---

## 🖼️ Image Management

### Product Images:
- **Featured Image**: Main product photo (1:1 aspect ratio)
- **Hover Image**: Alternative angle or action shot
- **Gallery Images**: Multiple product views

### Image Specifications:
```
Dimensions: 800x800px minimum
Format: JPG, PNG, WebP
Size: Under 500KB each
Background: White or transparent
Quality: High resolution, well-lit
```

### Image Types:
1. **Product Shot**: Clean, professional
2. **Lifestyle Shot**: In-use scenarios
3. **Detail Shot**: Close-up features
4. **Comparison Shot**: Size references
5. **Packaging Shot**: Unboxing appeal

---

## 📈 SEO & Marketing

### Product SEO:
- **Meta Title**: Include brand + product + "Bangladesh"
- **Meta Description**: Benefits + price + availability
- **URL Slug**: Clean, descriptive, keyword-rich

### Marketing Features:
- **Badges**: Budget Pick, Student Special, VIP Only
- **Urgency**: "Only 5 left", "Limited time"
- **Social Proof**: Reviews, ratings, testimonials
- **Bundles**: Related product suggestions

### Content Strategy:
```
Title Examples:
❌ "Gaming Mouse"
✅ "DeltaCrown Gaming Mouse Pro - Perfect for PUBG Mobile - ৳1,990"

Descriptions:
❌ "Good gaming mouse"
✅ "Precision gaming mouse designed for Bangladeshi mobile gamers. 
    Perfect for PUBG Mobile, Call of Duty Mobile, and Free Fire. 
    High DPI sensor ensures accurate shots every time."
```

---

## 🔧 Troubleshooting

### Common Issues:

#### 1. Images Not Loading
**Problem**: Product images show broken links
**Solution**:
```bash
# Collect static files
python manage.py collectstatic

# Check media settings in settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

#### 2. Prices Show Incorrectly
**Problem**: Still showing $ instead of ৳
**Solution**:
```python
# Make sure templates load bd_filters
{% load bd_filters %}

# Use proper filter
{{ product.price|bdt_currency }}
```

#### 3. Out of Stock Products Still Sellable
**Problem**: Can add out-of-stock items to cart
**Solution**:
```python
# Check product model
if product.track_stock and product.stock <= 0:
    # Disable add to cart button
```

#### 4. Categories Not Showing
**Problem**: Empty category pages
**Solution**:
- Verify products are assigned to categories
- Check category `is_active` status
- Ensure proper URL routing

### Database Maintenance:
```bash
# Reset sample data
python scripts/populate_crownstore.py

# Update prices for Bangladesh
python scripts/adapt_bangladesh_market.py

# Create admin user
python manage.py createsuperuser

# Run migrations
python manage.py migrate
```

---

## 📞 Support & Resources

### Quick Commands:
```bash
# Start development server
python manage.py runserver

# Access admin
http://127.0.0.1:8000/admin/

# View store
http://127.0.0.1:8000/crownstore/

# Run tests
python scripts/test_crownstore.py
```

### File Locations:
- **Models**: `apps/ecommerce/models.py`
- **Admin**: `apps/ecommerce/admin.py`
- **Templates**: `templates/ecommerce/`
- **Static Files**: `static/ecommerce/`
- **Scripts**: `scripts/`

### Need Help?
1. Check Django admin documentation
2. Review model field descriptions
3. Test with sample data first
4. Use provided scripts for automation
5. Monitor Django debug output

---

## 🎯 Best Practices for Bangladesh Market

### 1. Pricing Psychology
- End prices with 90, 99, or 95 (৳1,990 vs ৳2,000)
- Show savings prominently (৳500 saved!)
- Bundle complementary items
- Offer student discounts

### 2. Product Descriptions
- Mention popular games (PUBG, Free Fire)
- Include local context (perfect for Dhaka weather)
- Use relatable comparisons (gaming café hours)
- Highlight affordability

### 3. Cultural Sensitivity
- Respect local holidays and customs
- Use English (modern, international appeal)
- Include both urban and rural shipping
- Offer multiple payment methods

### 4. Trust Building
- Show real customer reviews
- Display clear return policy
- Provide local contact information
- Use Cash on Delivery option

---

**🚀 Ready to build Bangladesh's premier gaming store!**

*Last updated: October 2025*