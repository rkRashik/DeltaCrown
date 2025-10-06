"""
Comprehensive Fixes Script
==========================
1. Force dark mode on mobile for tournament hub
2. Add modern profile dropdown with theme toggle
3. Add scrolling navbar with glassy effect
4. Create new cyberpunk homepage
5. Modernize footer
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def append_to_css_file(filepath, css_content):
    """Append CSS content to a file"""
    full_path = os.path.join(BASE_DIR, filepath)
    with open(full_path, 'a', encoding='utf-8') as f:
        f.write('\n\n')
        f.write(css_content)
    print(f"✅ CSS appended to {filepath}")

def write_file(filepath, content):
    """Write content to a file"""
    full_path = os.path.join(BASE_DIR, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created {filepath}")

# =============================================================================
# 1. TOURNAMENT HUB MOBILE DARK MODE FIX
# =============================================================================

tournament_hub_mobile_css = """
/* ==========================================
   MOBILE DARK MODE FORCE FOR TOURNAMENT HUB
   ========================================== */

@media (max-width: 768px) {
    /* Force dark mode on mobile for tournament pages */
    body.tournament-hub-page,
    body.tournament-detail-page {
        background: #0a0e27 !important;
        color: #ffffff !important;
    }
    
    .tournament-hub,
    .tournament-detail-page {
        background: #0a0e27 !important;
    }
    
    .tournament-hub * {
        color: inherit !important;
    }
    
    .tournament-hub .card-bg,
    .tournament-hub .tournament-card {
        background: #141b2d !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
    }
}
"""

# =============================================================================
# 2. MODERN PROFILE DROPDOWN WITH THEME TOGGLE
# =============================================================================

profile_dropdown_css = """
/* ==========================================
   MODERN PREMIUM PROFILE DROPDOWN
   ========================================== */

.unified-nav-desktop__profile {
    position: relative;
}

.unified-nav-desktop__profile-menu {
    position: absolute;
    top: calc(100% + 12px);
    right: 0;
    min-width: 280px;
    background: linear-gradient(135deg, rgba(20, 27, 45, 0.98) 0%, rgba(10, 14, 39, 0.98) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0, 255, 136, 0.2);
    border-radius: 16px;
    box-shadow: 
        0 20px 60px rgba(0, 0, 0, 0.5),
        0 0 40px rgba(0, 255, 136, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
    padding: 0;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-10px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 9999;
}

.unified-nav-desktop__profile-menu.active {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}

/* Profile Header */
.profile-menu-header {
    padding: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}

.profile-menu-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    border: 3px solid #00ff88;
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
    margin: 0 auto 12px;
    display: block;
}

.profile-menu-name {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 4px;
}

.profile-menu-handle {
    font-size: 14px;
    color: #00ff88;
    font-family: 'Courier New', monospace;
}

/* Menu Items */
.profile-menu-items {
    padding: 8px 0;
}

.profile-menu-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    color: #b8c5d6;
    text-decoration: none;
    transition: all 0.2s ease;
    cursor: pointer;
    border: none;
    background: transparent;
    width: 100%;
    text-align: left;
    font-size: 14px;
}

.profile-menu-item svg {
    width: 18px;
    height: 18px;
    opacity: 0.7;
}

.profile-menu-item:hover {
    background: rgba(0, 255, 136, 0.1);
    color: #00ff88;
    transform: translateX(4px);
}

.profile-menu-item:hover svg {
    opacity: 1;
}

/* Theme Toggle */
.profile-theme-toggle {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: 8px;
    padding-top: 8px;
}

.theme-toggle-track {
    position: relative;
    width: 48px;
    height: 24px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-left: auto;
    transition: background 0.3s ease;
}

.theme-toggle-input:checked ~ .theme-toggle-track {
    background: rgba(0, 255, 136, 0.2);
}

.theme-toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: #ffffff;
    border-radius: 50%;
    transition: transform 0.3s ease;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.theme-toggle-input:checked ~ .theme-toggle-track .theme-toggle-thumb {
    transform: translateX(24px);
}

.theme-toggle-icon {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 12px;
    height: 12px;
    transition: opacity 0.3s ease;
}

.theme-toggle-icon--sun {
    left: 4px;
    color: #ffd700;
}

.theme-toggle-icon--moon {
    right: 4px;
    color: #4a90e2;
}

.theme-toggle-input:checked ~ .theme-toggle-track .theme-toggle-icon--sun {
    opacity: 0.3;
}

.theme-toggle-input ~ .theme-toggle-track .theme-toggle-icon--moon {
    opacity: 0.3;
}

.theme-toggle-input:checked ~ .theme-toggle-track .theme-toggle-icon--moon {
    opacity: 1;
}

/* Sign Out */
.profile-menu-signout {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin-top: 8px;
    color: #ff4757 !important;
}

.profile-menu-signout:hover {
    background: rgba(255, 71, 87, 0.1) !important;
    color: #ff4757 !important;
}
"""

# =============================================================================
# 3. SCROLLING NAVBAR WITH GLASSY EFFECT
# =============================================================================

scrolling_navbar_css = """
/* ==========================================
   SCROLLING NAVBAR WITH GLASSY EFFECT
   ========================================== */

.unified-nav-desktop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: transparent;
    backdrop-filter: none;
    border-bottom: 1px solid transparent;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 1000;
}

/* Scrolled State */
.unified-nav-desktop.scrolled {
    background: rgba(11, 18, 32, 0.85);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(0, 255, 136, 0.15);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.unified-nav-desktop.scrolled .unified-nav-desktop__container {
    height: 60px;
}

/* Initial state - larger, more prominent */
.unified-nav-desktop__container {
    height: 70px;
    transition: height 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Logo animations on scroll */
.unified-nav-desktop__logo,
.unified-nav-desktop__wordmark {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.unified-nav-desktop.scrolled .unified-nav-desktop__logo {
    width: 36px;
    height: 36px;
}

.unified-nav-desktop.scrolled .unified-nav-desktop__wordmark {
    height: 24px;
}

/* Add glow effect on scroll */
.unified-nav-desktop.scrolled::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(0, 255, 136, 0.3) 50%, 
        transparent 100%);
}
"""

# =============================================================================
# APPLY CSS FIXES
# =============================================================================

print("\n🚀 Applying CSS fixes...")
print("=" * 50)

append_to_css_file(
    'static/tournaments/css/tournament-detail-modern.css',
    tournament_hub_mobile_css
)

append_to_css_file(
    'static/siteui/css/navigation-unified.css',
    profile_dropdown_css + scrolling_navbar_css
)

print("\n✅ All CSS fixes applied successfully!")
print("=" * 50)
