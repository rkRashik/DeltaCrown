"""
Bangladesh-specific template filters for CrownStore
Includes currency formatting and localization
"""

from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def bdt_currency(value):
    """
    Format price in Bangladeshi Taka with proper formatting
    Example: 1500 -> "৳1,500"
    """
    try:
        if value is None:
            return "৳0"
        
        # Convert to Decimal for precise formatting
        amount = Decimal(str(value))
        
        # Format with commas for thousands
        formatted = "{:,.0f}".format(amount)
        
        return f"৳{formatted}"
    except (ValueError, TypeError):
        return "৳0"

@register.filter
def bdt_short(value):
    """
    Format large amounts in short form
    Example: 15000 -> "৳15K", 1500000 -> "৳15L"
    """
    try:
        if value is None:
            return "৳0"
        
        amount = float(value)
        
        if amount >= 10000000:  # 1 Crore
            return f"৳{amount/10000000:.1f}Cr"
        elif amount >= 100000:  # 1 Lakh
            return f"৳{amount/100000:.1f}L"
        elif amount >= 1000:  # 1 Thousand
            return f"৳{amount/1000:.1f}K"
        else:
            return f"৳{amount:,.0f}"
    except (ValueError, TypeError):
        return "৳0"

@register.filter
def savings_amount(original, current):
    """
    Calculate savings amount in BDT
    """
    try:
        if not original or not current:
            return "৳0"
        
        savings = float(original) - float(current)
        if savings > 0:
            return bdt_currency(savings)
        return "৳0"
    except (ValueError, TypeError):
        return "৳0"

@register.filter
def is_affordable(price):
    """
    Check if price is in affordable range for Bangladeshi students
    """
    try:
        amount = float(price)
        return amount <= 3000  # Under 3000 BDT considered affordable
    except (ValueError, TypeError):
        return False

@register.filter
def price_category(price):
    """
    Categorize price for Bangladeshi market
    """
    try:
        amount = float(price)
        if amount <= 1000:
            return "budget"
        elif amount <= 3000:
            return "affordable"
        elif amount <= 8000:
            return "premium"
        else:
            return "luxury"
    except (ValueError, TypeError):
        return "budget"

@register.simple_tag
def bd_market_badge(product):
    """
    Generate market-appropriate badge for Bangladesh
    """
    try:
        price = float(product.price)
        
        if price <= 1000:
            return '<span class="market-badge budget">💰 Budget Pick</span>'
        elif price <= 2000:
            return '<span class="market-badge student">🎓 Student Special</span>'
        elif product.is_member_exclusive:
            return '<span class="market-badge exclusive">👑 VIP Only</span>'
        elif product.is_limited_edition:
            return '<span class="market-badge limited">🔥 Limited Time</span>'
        elif product.is_featured:
            return '<span class="market-badge featured">⭐ Top Pick</span>'
        else:
            return ''
    except:
        return ''

@register.inclusion_tag('ecommerce/partials/bd_payment_methods.html')
def bd_payment_methods():
    """
    Render Bangladesh-specific payment methods
    """
    return {
        'methods': [
            {'name': 'bKash', 'icon': 'fab fa-btc', 'popular': True},
            {'name': 'Nagad', 'icon': 'fas fa-mobile-alt', 'popular': True},
            {'name': 'Rocket', 'icon': 'fas fa-rocket', 'popular': False},
            {'name': 'Bank Transfer', 'icon': 'fas fa-university', 'popular': False},
            {'name': 'Cash on Delivery', 'icon': 'fas fa-truck', 'popular': True},
        ]
    }

@register.filter
def gaming_time_friendly(value):
    """
    Convert price to gaming time equivalent for perspective
    Example: "৳2000 = 40 hours of gaming café"
    """
    try:
        amount = float(value)
        cafe_rate = 50  # BDT per hour at gaming café
        hours = amount / cafe_rate
        
        if hours >= 24:
            days = hours / 24
            return f"= {days:.0f} days of gaming café"
        else:
            return f"= {hours:.0f} hours of gaming café"
    except:
        return ""
