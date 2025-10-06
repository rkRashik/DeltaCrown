"""
Fix all tournament hub and navigation issues
"""

# Issue 1: Force dark mode for tournament hub
hub_dark_mode_css = """
/* Force Dark Mode for Tournament Hub */
.tournament-hub {
    background-color: #050816 !important;
    color: #ffffff !important;
}

.tournament-hub * {
    color: inherit;
}

.tournament-hub .dc-hub-hero {
    background: linear-gradient(135deg, #0a0e27 0%, #050816 100%);
}

.tournament-hub .dc-tournament-card {
    background: rgba(20, 27, 45, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
}

.tournament-hub .dc-tournament-card__title {
    color: #ffffff !important;
}

.tournament-hub .dc-tournament-card__text {
    color: #b8c5d6 !important;
}

.tournament-hub .dc-game-card {
    background: rgba(20, 27, 45, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
}

.tournament-hub .dc-filter-pill {
    background: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.tournament-hub .dc-filter-pill.active {
    background: #00ff88;
    color: #000;
}
"""

# Issue 2: Mobile responsive fixes for tournament detail page
detail_mobile_css = """
/* Mobile Responsive Fixes for Tournament Detail Page */
@media (max-width: 768px) {
    .tournament-detail-page .hero-banner {
        min-height: 400px;
        padding-bottom: 20px;
    }
    
    .tournament-detail-page .hero-title {
        font-size: 32px !important;
    }
    
    .tournament-detail-page .hero-info-grid {
        grid-template-columns: 1fr !important;
        gap: 12px;
    }
    
    .tournament-detail-page .action-card-premium {
        padding: 20px !important;
        margin: 0 -20px;
        border-radius: 0;
    }
    
    .tournament-detail-page .btn-content {
        flex-direction: column;
        text-align: center;
        gap: 12px;
    }
    
    .tournament-detail-page .btn-text {
        align-items: center;
    }
    
    .tournament-detail-page .action-features {
        grid-template-columns: 1fr !important;
        gap: 8px;
    }
    
    .tournament-detail-page .content-layout {
        grid-template-columns: 1fr !important;
    }
    
    .tournament-detail-page .stats-showcase {
        grid-template-columns: 1fr !important;
    }
    
    .tournament-detail-page .countdown-timer-premium {
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 8px;
    }
    
    .tournament-detail-page .countdown-divider {
        display: none !important;
    }
}

@media (max-width: 480px) {
    .tournament-detail-page .container {
        padding: 0 16px !important;
    }
    
    .tournament-detail-page .hero-title {
        font-size: 24px !important;
    }
    
    .tournament-detail-page .btn-title {
        font-size: 16px !important;
    }
}
"""

# Save CSS fixes
import os

css_file_path = r'G:\My Projects\WORK\DeltaCrown\static\tournaments\css\tournament-detail-modern.css'

with open(css_file_path, 'a', encoding='utf-8') as f:
    f.write('\n\n' + hub_dark_mode_css)
    f.write('\n\n' + detail_mobile_css)

print("✅ CSS fixes applied!")
print("  - Tournament hub forced to dark mode")
print("  - Tournament detail made mobile responsive")
