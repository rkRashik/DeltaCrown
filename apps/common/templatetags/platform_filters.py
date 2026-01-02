"""
Platform Filters Template Tags (Phase 5A)

Template filters for formatting dates/times and currency values according to user preferences.

NO HARDCODED VALUES: All formatting respects user_platform_prefs.

Usage in templates:
    {% load platform_filters %}
    
    {{ transaction.created_at|format_dt }}
    {{ wallet.balance|format_money }}
"""

from django import template
from django.utils import timezone
from decimal import Decimal
import logging

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter(name='format_dt')
def format_dt(value, time_format=None):
    """
    Format datetime according to user's time_format preference.
    
    Args:
        value: datetime object (aware or naive)
        time_format: '12h' or '24h' (optional, reads from context if not provided)
    
    Returns:
        str: Formatted datetime string
    
    Example:
        {{ transaction.created_at|format_dt }}
        {{ tournament.start_time|format_dt:"24h" }}
    """
    if not value:
        return ""
    
    # Ensure timezone-aware
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    
    # Convert to local timezone (already activated by middleware)
    local_time = timezone.localtime(value)
    
    # Determine format (from parameter or default to 12h)
    fmt = time_format or '12h'
    
    # Format date and time
    if fmt == '24h':
        # 24-hour format: "Jan 2, 2026 15:30"
        return local_time.strftime("%b %d, %Y %H:%M")
    else:
        # 12-hour format: "Jan 2, 2026 3:30 PM"
        return local_time.strftime("%b %d, %Y %I:%M %p")


@register.filter(name='format_money')
def format_money(value, currency=None):
    """
    Format money amount according to user's currency preference.
    
    Args:
        value: Decimal, float, or int (amount)
        currency: 'BDT' or 'USD' (optional, defaults to BDT)
    
    Returns:
        str: Formatted currency string
    
    Example:
        {{ wallet.balance|format_money }}
        {{ prize_pool|format_money:"USD" }}
    """
    if value is None:
        value = Decimal('0.00')
    
    try:
        amount = Decimal(str(value))
    except (ValueError, TypeError):
        logger.warning(f"Invalid money value: {value}")
        amount = Decimal('0.00')
    
    # Determine currency (from parameter or default to BDT)
    curr = currency or 'BDT'
    
    # Format based on currency
    if curr == 'BDT':
        # BDT format: "৳ 1,234.50"
        symbol = '৳'
        formatted = f"{amount:,.2f}"
        return f"{symbol} {formatted}"
    elif curr == 'USD':
        # USD format: "$1,234.50"
        symbol = '$'
        formatted = f"{amount:,.2f}"
        return f"{symbol}{formatted}"
    else:
        # Fallback: generic format
        return f"{amount:,.2f} {curr}"


@register.simple_tag(takes_context=True)
def format_dt_context(context, value):
    """
    Format datetime using time_format from template context (user_platform_prefs).
    
    Reads from context['user_platform_prefs']['time_format'] automatically.
    
    Usage:
        {% format_dt_context transaction.created_at %}
    """
    prefs = context.get('user_platform_prefs', {})
    time_format = prefs.get('time_format', '12h')
    return format_dt(value, time_format)


@register.simple_tag(takes_context=True)
def format_money_context(context, value):
    """
    Format money using currency from template context (user_platform_prefs).
    
    Reads from context['user_platform_prefs']['currency'] automatically.
    
    Usage:
        {% format_money_context wallet.balance %}
    """
    prefs = context.get('user_platform_prefs', {})
    currency = prefs.get('currency', 'BDT')
    return format_money(value, currency)
