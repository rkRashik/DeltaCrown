"""
Homepage Context Configuration
=============================
Controls all homepage content, features, and display settings.
"""

from django.conf import settings
from apps.common.game_assets import GAMES


def homepage_context(request):
    """
    Homepage context processor providing all homepage configuration.
    """
    
    # Hero Section Configuration
    hero_config = {
        'title': 'Level Up Your Game',
        'subtitle': 'Premier Esports Platform',
        'description': 'Join thousands of gamers in competitive tournaments. Climb rankings, earn rewards, and become a legend.',
        'cta_primary': {
            'text': 'Start Competing',
            'url': '/tournaments/',
            'icon': 'fa-trophy'
        },
        'cta_secondary': {
            'text': 'Browse Teams',
            'url': '/teams/',
            'icon': 'fa-users'
        },
        'background_video': 'videos/hero-bg.mp4',  # Optional video background
        'background_image': 'img/hero/esports-arena.jpg',
        'overlay_opacity': 0.7
    }
    
    # Featured Games Configuration
    featured_games = [
        {
            'code': 'VALORANT',
            'highlight': True,
            'tournaments_count': 12,
            'players_count': 2847,
            'featured_tournament': {
                'name': 'Valorant Champions Cup',
                'prize': '৳50,000',
                'starts_in': '2 days'
            }
        },
        {
            'code': 'EFOOTBALL',
            'highlight': True,
            'tournaments_count': 8,
            'players_count': 1923,
            'featured_tournament': {
                'name': 'eFootball Premier League',
                'prize': '৳35,000',
                'starts_in': '5 days'
            }
        },
        {
            'code': 'CS2',
            'highlight': True,
            'tournaments_count': 6,
            'players_count': 1456,
            'featured_tournament': {
                'name': 'Counter-Strike Elite',
                'prize': '৳40,000',
                'starts_in': '1 week'
            }
        },
        {
            'code': 'MLBB',
            'highlight': False,
            'tournaments_count': 15,
            'players_count': 3201,
        },
        {
            'code': 'PUBG',
            'highlight': False,
            'tournaments_count': 9,
            'players_count': 2134,
        },
        {
            'code': 'FC26',
            'highlight': False,
            'tournaments_count': 4,
            'players_count': 892,
        }
    ]
    
    # Platform Statistics
    platform_stats = {
        'total_tournaments': 156,
        'active_players': 12847,
        'total_prizes': '৳2,50,000',
        'communities': 8,
        'growth_rate': '+23%'
    }
    
    # Features Section
    features = [
        {
            'icon': 'fa-trophy',
            'title': 'Competitive Tournaments',
            'description': 'Join ranked tournaments with verified prizes and fair matchmaking.',
            'color': '#FF6B35'
        },
        {
            'icon': 'fa-chart-line',
            'title': 'Real-time Rankings',
            'description': 'Track your progress with live leaderboards and performance analytics.',
            'color': '#4ECDC4'
        },
        {
            'icon': 'fa-shield-alt',
            'title': 'Anti-Cheat Security',
            'description': 'Advanced detection systems ensure fair play for all participants.',
            'color': '#45B7D1'
        },
        {
            'icon': 'fa-money-bill-wave',
            'title': 'Instant Payouts',
            'description': 'Win and get paid instantly through our secure payment system.',
            'color': '#96CEB4'
        },
        {
            'icon': 'fa-users',
            'title': 'Team Management',
            'description': 'Create and manage professional esports teams with advanced tools.',
            'color': '#FFEAA7'
        },
        {
            'icon': 'fa-broadcast-tower',
            'title': 'Live Streaming',
            'description': 'Stream your matches and build your audience with integrated tools.',
            'color': '#DDA0DD'
        }
    ]
    
    # Testimonials
    testimonials = [
        {
            'name': 'Akash Rahman',
            'team': 'Team Phoenix',
            'game': 'Valorant',
            'avatar': 'img/avatars/player1.jpg',
            'rating': 5,
            'text': 'DeltaCrown helped me find my competitive edge. The tournaments are well-organized and the community is incredible.',
            'verified': True
        },
        {
            'name': 'Nadia Islam',
            'team': 'Storm Riders',
            'game': 'Mobile Legends',
            'avatar': 'img/avatars/player2.jpg',
            'rating': 5,
            'text': 'Best platform for esports in Bangladesh. Fair matchmaking and instant prize distribution!',
            'verified': True
        },
        {
            'name': 'Rifat Ahmed',
            'team': 'Cyber Wolves',
            'game': 'CS2',
            'avatar': 'img/avatars/player3.jpg',
            'rating': 5,
            'text': 'Professional tournament experience with great anti-cheat systems. Highly recommend!',
            'verified': True
        }
    ]
    
    # Recent News & Updates
    news_updates = [
        {
            'title': 'DeltaCrown Championship 2025 Announced',
            'excerpt': 'Biggest esports tournament in Bangladesh with ৳5,00,000 prize pool.',
            'image': 'img/news/championship-2025.jpg',
            'date': '2025-09-25',
            'category': 'Tournament',
            'url': '/news/championship-2025/'
        },
        {
            'title': 'New Anti-Cheat System Launch',
            'excerpt': 'Advanced AI-powered detection system ensures 100% fair play.',
            'image': 'img/news/anticheat-launch.jpg',
            'date': '2025-09-20',
            'category': 'Technology',
            'url': '/news/anticheat-system/'
        },
        {
            'title': 'Mobile Gaming Expansion',
            'excerpt': 'Added support for 5 new mobile games including Free Fire and COD Mobile.',
            'image': 'img/news/mobile-expansion.jpg',
            'date': '2025-09-15',
            'category': 'Games',
            'url': '/news/mobile-expansion/'
        }
    ]
    
    # Call-to-Action Sections
    cta_sections = {
        'tournaments': {
            'title': 'Ready to Compete?',
            'subtitle': 'Join active tournaments and start your esports journey',
            'button_text': 'View Tournaments',
            'button_url': '/tournaments/',
            'background_gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
        },
        'teams': {
            'title': 'Build Your Legacy',
            'subtitle': 'Create or join professional esports teams',
            'button_text': 'Explore Teams',
            'button_url': '/teams/',
            'background_gradient': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
        }
    }
    
    # Theme Configuration
    theme_config = {
        'primary_color': '#FF6B35',
        'secondary_color': '#4ECDC4',
        'accent_color': '#45B7D1',
        'success_color': '#96CEB4',
        'warning_color': '#FFEAA7',
        'danger_color': '#FF7675',
        'dark_bg': '#0a0a0a',
        'dark_surface': '#1a1a1a',
        'dark_text': '#ffffff',
        'light_bg': '#ffffff',
        'light_surface': '#f8f9fa',
        'light_text': '#333333'
    }
    
    # Animation Settings
    animation_config = {
        'hero_particles': True,
        'scroll_reveal': True,
        'hover_effects': True,
        'loading_animations': True,
        'transition_duration': '0.3s',
        'easing': 'cubic-bezier(0.4, 0, 0.2, 1)'
    }
    
    return {
        'homepage': {
            'hero': hero_config,
            'featured_games': featured_games,
            'platform_stats': platform_stats,
            'features': features,
            'testimonials': testimonials,
            'news_updates': news_updates,
            'cta_sections': cta_sections,
            'theme': theme_config,
            'animations': animation_config,
            'games': GAMES,  # Include all game assets
        }
    }