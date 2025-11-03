# apps/tournaments/views/_deprecated.py
"""
Deprecated Registration Views - For Backward Compatibility Only

⚠️ WARNING: These views are deprecated and will be removed in a future version.
⚠️ Use modern_register_view instead.

Legacy views maintained here for backward compatibility:
- register() - Original registration view
- unified_register() - Unified registration system
- enhanced_register() - Enhanced registration system
- valorant_register() - Game-specific registration
- efootball_register() - Game-specific registration

Migration Path:
1. Update all links to use 'tournaments:modern_register' URL name
2. Update templates to use {% url 'tournaments:modern_register' slug %}
3. Remove references to deprecated URL names
4. Test thoroughly
5. These views will be removed in next major version

Modern Registration Benefits:
✅ Uses centralized state machine
✅ Multi-step form with validation
✅ Auto-fill from profile/team data
✅ Real-time state updates
✅ Better error handling
✅ REST API support
✅ Request approval workflow
"""
import warnings
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


def deprecated_view(replacement_view_name: str, removal_version: str = "2.0"):
    """
    Decorator to mark views as deprecated and redirect to modern replacement.
    
    Args:
        replacement_view_name: Name of the modern view to redirect to
        removal_version: Version when this will be removed
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, slug, *args, **kwargs):
            # Log deprecation warning
            warnings.warn(
                f"{func.__name__} is deprecated and will be removed in version {removal_version}. "
                f"Use {replacement_view_name} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            
            # Show user-friendly message
            messages.warning(
                request,
                "You're using a legacy registration page. "
                "Redirecting to the improved registration system..."
            )
            
            # Redirect to modern view
            return redirect(reverse(replacement_view_name, kwargs={'slug': slug}))
        
        return wrapper
    return decorator


# Import legacy views
from .registration import register as _register_legacy
from .registration_unified import (
    unified_register as _unified_register_legacy,
    valorant_register as _valorant_register_legacy,
    efootball_register as _efootball_register_legacy,
)
from .enhanced_registration import enhanced_register as _enhanced_register_legacy


# Wrap with deprecation decorator
@deprecated_view('tournaments:modern_register', '2.0')
def register(request, slug):
    """
    DEPRECATED: Original registration view.
    Redirects to modern_register_view.
    """
    return _register_legacy(request, slug)


@deprecated_view('tournaments:modern_register', '2.0')
def unified_register(request, slug):
    """
    DEPRECATED: Unified registration system.
    Redirects to modern_register_view.
    """
    return _unified_register_legacy(request, slug)


@deprecated_view('tournaments:modern_register', '2.0')
def enhanced_register(request, slug):
    """
    DEPRECATED: Enhanced registration system.
    Redirects to modern_register_view.
    """
    return _enhanced_register_legacy(request, slug)


@deprecated_view('tournaments:modern_register', '2.0')
def valorant_register(request, slug):
    """
    DEPRECATED: Valorant-specific registration.
    Redirects to modern_register_view (game-agnostic).
    """
    return _valorant_register_legacy(request, slug)


@deprecated_view('tournaments:modern_register', '2.0')
def efootball_register(request, slug):
    """
    DEPRECATED: eFootball-specific registration.
    Redirects to modern_register_view (game-agnostic).
    """
    return _efootball_register_legacy(request, slug)


# Export for backward compatibility
__all__ = [
    'register',
    'unified_register',
    'enhanced_register',
    'valorant_register',
    'efootball_register',
]
