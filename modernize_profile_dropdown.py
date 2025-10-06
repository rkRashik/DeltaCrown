"""
Modernize profile dropdown design and ensure theme toggle works properly
"""

modern_dropdown_css = """
/* ============================================
   MODERN PREMIUM PROFILE DROPDOWN
   ============================================ */

.profile-menu {
    min-width: 320px;
    background: linear-gradient(135deg, rgba(20, 27, 45, 0.98) 0%, rgba(10, 14, 39, 0.98) 100%);
    border-radius: 16px;
    box-shadow: 
        0 20px 60px rgba(0, 0, 0, 0.5),
        0 0 0 1px rgba(255, 255, 255, 0.1),
        0 0 40px rgba(0, 255, 136, 0.1);
    padding: 0;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    animation: dropdownFadeIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes dropdownFadeIn {
    from {
        opacity: 0;
        transform: translateY(-10px) scale(0.95);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* Profile Header */
.profile-menu-header {
    padding: 24px;
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 212, 255, 0.1) 100%);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    align-items: center;
    gap: 16px;
}

.profile-menu-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    overflow: hidden;
    border: 3px solid rgba(0, 255, 136, 0.5);
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
    flex-shrink: 0;
}

.profile-menu-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.profile-menu-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 0;
}

.profile-menu-name {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
    font-family: 'Rajdhani', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.profile-menu-handle {
    font-size: 13px;
    color: #00ff88;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Menu Sections */
.profile-menu-section {
    padding: 16px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.profile-menu-section:last-child {
    border-bottom: none;
}

.profile-menu-heading {
    display: block;
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #7a8699;
    margin-bottom: 4px;
}

/* Menu Items */
.profile-menu-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    color: #b8c5d6;
    text-decoration: none;
    font-size: 14px;
    font-weight: 600;
    border-radius: 10px;
    margin: 2px 4px;
    transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    cursor: pointer;
}

.profile-menu-item:hover {
    background: rgba(0, 255, 136, 0.1);
    color: #00ff88;
    transform: translateX(4px);
}

.profile-menu-item:active {
    transform: translateX(4px) scale(0.98);
}

/* Theme Toggle in Dropdown */
.profile-theme-toggle {
    position: relative;
}

.profile-theme-sun,
.profile-theme-moon {
    width: 18px;
    height: 18px;
    transition: all 0.3s ease;
}

.profile-theme-sun {
    color: #ffa500;
}

.profile-theme-moon {
    color: #00d4ff;
    display: none;
}

:root[data-theme="light"] .profile-theme-sun {
    display: none;
}

:root[data-theme="light"] .profile-theme-moon {
    display: block;
}

.profile-theme-text {
    flex: 1;
}

.profile-theme-toggle:hover .profile-theme-sun,
.profile-theme-toggle:hover .profile-theme-moon {
    transform: rotate(15deg) scale(1.1);
}

/* Sign Out Button */
.profile-menu-signout {
    color: #ff4757 !important;
}

.profile-menu-signout:hover {
    background: rgba(255, 71, 87, 0.15) !important;
    color: #ff4757 !important;
}

/* Avatar Button */
.profile-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    overflow: hidden;
    position: relative;
    border: 2px solid rgba(0, 255, 136, 0.5);
    transition: all 0.3s ease;
}

.profile-avatar:hover {
    border-color: #00ff88;
    box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
    transform: scale(1.05);
}

.profile-avatar-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.avatar-fallback {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
    color: #000;
    font-weight: 900;
    font-size: 16px;
    font-family: 'Rajdhani', sans-serif;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .profile-menu {
        min-width: 280px;
        right: 10px;
    }
    
    .profile-menu-header {
        padding: 20px;
    }
    
    .profile-menu-avatar {
        width: 48px;
        height: 48px;
    }
    
    .profile-menu-name {
        font-size: 14px;
    }
    
    .profile-menu-item {
        padding: 10px 14px;
        font-size: 13px;
    }
}

/* Dark mode by default */
:root {
    --profile-bg: rgba(20, 27, 45, 0.98);
    --profile-text: #ffffff;
    --profile-accent: #00ff88;
}

/* Ensure dropdown is positioned correctly */
.profile-dropdown {
    position: relative;
}

.profile-dropdown .dropdown-menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 1000;
}

/* Add icon spacing */
.profile-menu-item::before {
    content: '';
    width: 4px;
    height: 4px;
    background: currentColor;
    border-radius: 50%;
    opacity: 0;
    transition: opacity 0.2s ease;
}

.profile-menu-item:hover::before {
    opacity: 1;
}
"""

# Write the CSS
css_file_path = r'G:\My Projects\WORK\DeltaCrown\static\siteui\css\navigation-unified.css'

with open(css_file_path, 'a', encoding='utf-8') as f:
    f.write('\n\n' + modern_dropdown_css)

print("✅ Modern profile dropdown CSS applied!")
print("  - Premium esports design")
print("  - Theme toggle integrated")
print("  - Mobile responsive")
print("  - Smooth animations")
