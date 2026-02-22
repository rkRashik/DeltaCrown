"""
Homepage Context Configuration - Cyberpunk         {
            'code': 'VAL',
            'name': 'Valorant',
            'tagline': 'Tactical 5v5 Shooter',
            'logo': 'img/game_logos/valorant_logo.svg',
            'banner': 'img/game_cards/valorant.jpeg',
            'color': '#FF4655',
            'glow': 'rgba(255, 70, 85, 0.4)',
            'platforms': ['PC'],
            'tournaments_active': get_game_tournament_count('valorant'),
            'players_online': get_game_player_count('valorant'),
            'prize_pool': '৳75,000',
            'url': '/tournaments/?game=valorant',
            'featured': True,
        },============================================
Modern, dynamic context processor for the cyberpunk-themed homepage.
All configuration in one place for easy updates.
"""

from django.conf import settings
from django.utils import timezone
from django.apps import apps
from datetime import timedelta
from apps.common.game_assets import GAMES


def homepage_context(request):
    """
    Comprehensive homepage context with live data and static content.
    """
    # Skip on admin pages — none of this data is used there
    if request.path.startswith('/admin/'):
        return {}
    
    # ================================================================
    # HERO SECTION - Dynamic Tournament Feature
    # ================================================================
    
    featured_tournament = get_featured_tournament()
    
    hero = {
        'title': 'Dominate The Arena',
        'subtitle': 'Bangladesh\'s Premier Esports Platform',
        'description': 'Compete in legendary tournaments. Earn glory. Claim prizes. Join thousands of gamers in the ultimate competitive experience.',
        'cta_primary': {
            'text': 'Join Tournament',
            'url': featured_tournament['url'] if featured_tournament else '/tournaments/',
            'icon': '⚡'
        },
        'cta_secondary': {
            'text': 'Explore Games',
            'url': '#games',
            'icon': '🎮'
        },
        'featured_tournament': featured_tournament,
        'stats': get_live_stats(),
    }
    
    # ================================================================
    # GAMES SHOWCASE - Main Games Grid
    # ================================================================
    
    games = [
        {
            'code': 'VALORANT',
            'name': 'Valorant',
            'tagline': 'Tactical Shooter',
            'logo': 'img/game_logos/Valorant_logo.jpg',
            'banner': 'img/game_cards/Valorant.jpg',
            'color': '#FF4655',
            'glow': 'rgba(255, 70, 85, 0.4)',
            'tournaments_active': get_game_tournament_count('valorant'),
            'players_online': get_game_player_count('valorant'),
            'prize_pool': '৳85,000',
            'url': '/tournaments/?game=valorant',
            'featured': True,
        },
        {
            'code': 'EFOOTBALL',
            'name': 'eFootball',
            'tagline': 'Virtual Stadium',
            'logo': 'img/game_logos/efootball_logo.jpeg',
            'banner': 'img/game_cards/efootball.jpeg',
            'color': '#00FF88',
            'glow': 'rgba(0, 255, 136, 0.4)',
            'tournaments_active': get_game_tournament_count('efootball'),
            'players_online': get_game_player_count('efootball'),
            'prize_pool': '৳65,000',
            'url': '/tournaments/?game=efootball',
            'featured': True,
        },
        {
            'code': 'CS2',
            'name': 'Counter-Strike 2',
            'tagline': 'Tactical FPS',
            'logo': 'img/game_logos/CS2_logo.jpeg',
            'banner': 'img/game_cards/CS2.jpg',
            'color': '#F79100',
            'glow': 'rgba(247, 145, 0, 0.4)',
            'tournaments_active': get_game_tournament_count('cs2'),
            'players_online': get_game_player_count('cs2'),
            'prize_pool': '৳75,000',
            'url': '/tournaments/?game=cs2',
            'featured': True,
        },
        {
            'code': 'MLBB',
            'name': 'Mobile Legends',
            'tagline': 'MOBA Battle',
            'logo': 'img/game_logos/mobile_legend_logo.jpeg',
            'banner': 'img/game_cards/MobileLegend.jpg',
            'color': '#4169E1',
            'glow': 'rgba(65, 105, 225, 0.4)',
            'tournaments_active': get_game_tournament_count('mlbb'),
            'players_online': get_game_player_count('mlbb'),
            'prize_pool': '৳55,000',
            'url': '/tournaments/?game=mlbb',
            'featured': False,
        },
        {
            'code': 'PUBG',
            'name': 'PUBG Mobile',
            'tagline': 'Battle Royale',
            'logo': 'img/game_logos/PUBG_logo.jpg',
            'banner': 'img/game_cards/PUBG.jpeg',
            'color': '#FFB800',
            'glow': 'rgba(255, 184, 0, 0.4)',
            'platforms': ['Mobile', 'iOS', 'Android'],
            'tournaments_active': get_game_tournament_count('pubg'),
            'players_online': get_game_player_count('pubg'),
            'prize_pool': '৳45,000',
            'url': '/tournaments/?game=pubg',
            'featured': False,
        },
        {
            'code': 'FC26',
            'name': 'EA Sports FC 26',
            'tagline': 'Football Simulation',
            'logo': 'img/game_logos/fc26_logo.jpg',
            'banner': 'img/game_cards/FC26.jpg',
            'color': '#00D8FF',
            'glow': 'rgba(0, 216, 255, 0.4)',
            'platforms': ['PC', 'PS5', 'Xbox'],
            'tournaments_active': get_game_tournament_count('fc26'),
            'players_online': get_game_player_count('fc26'),
            'prize_pool': '৳35,000',
            'url': '/tournaments/?game=fc26',
            'featured': False,
        },
    ]
    
    # ================================================================
    # PLATFORM FEATURES - Why Choose DeltaCrown
    # ================================================================
    
    features = [
        {
            'icon': '🏆',
            'title': 'Verified Tournaments',
            'description': 'Professionally organized tournaments with guaranteed prize pools and fair rules.',
            'color': '#FF4655',
        },
        {
            'icon': '⚡',
            'title': 'Instant Payouts',
            'description': 'Win and get paid immediately through our secure instant payment system.',
            'color': '#FFB800',
        },
        {
            'icon': '🎯',
            'title': 'Skill-Based Matching',
            'description': 'Advanced matchmaking ensures fair competition at your skill level.',
            'color': '#00FF88',
        },
        {
            'icon': '🛡️',
            'title': 'Anti-Cheat Protection',
            'description': 'State-of-the-art detection systems for a completely fair playing field.',
            'color': '#4169E1',
        },
        {
            'icon': '📊',
            'title': 'Live Rankings',
            'description': 'Real-time leaderboards and comprehensive performance analytics.',
            'color': '#F79100',
        },
        {
            'icon': '👥',
            'title': 'Team Management',
            'description': 'Build and manage professional esports teams with powerful tools.',
            'color': '#00D8FF',
        },
    ]
    
    # ================================================================
    # LIVE TOURNAMENTS - Currently Active
    # ================================================================
    
    live_tournaments = get_live_tournaments()
    
    # ================================================================
    # UPCOMING EVENTS - Next 7 Days
    # ================================================================
    
    upcoming_events = get_upcoming_events()
    
    # ================================================================
    # TESTIMONIALS - Removed (replaced with stats showcase)
    # ================================================================
    
    testimonials = []
    
    # ================================================================
    # CALL TO ACTION - Join Community
    # ================================================================
    
    cta = {
        'title': 'Ready To Compete?',
        'subtitle': 'Join thousands of gamers in the ultimate competitive experience',
        'button_text': 'Create Free Account',
        'button_url': '/accounts/signup/' if not request.user.is_authenticated else '/tournaments/',
    }
    
    # ================================================================
    # RETURN COMPLETE CONTEXT
    # ================================================================
    
    return {
        'homepage': {
            'hero': hero,
            'games': games,
            'features': features,
            'live_tournaments': live_tournaments,
            'upcoming_events': upcoming_events,
            'testimonials': testimonials,
            'cta': cta,
        }
    }


# =======================================================================
# HELPER FUNCTIONS - Dynamic Data Fetching
# =======================================================================

def get_featured_tournament():
    """Get the next featured tournament or most recent"""
    try:
        Tournament = apps.get_model('tournaments', 'Tournament')
        now = timezone.now()
        
        # Try to get next upcoming tournament
        tournament = Tournament.objects.filter(
            tournament_start__gte=now
        ).order_by('tournament_start').first()
        
        # Fallback to latest tournament
        if not tournament:
            tournament = Tournament.objects.order_by('-id').first()
        
        if tournament:
            return {
                'name': tournament.name,
                'game': getattr(getattr(tournament, 'game', None), 'name', 'Unknown'),
                'prize': f"৳{tournament.prize_pool or 0:,}",
                'date': getattr(tournament, 'tournament_start', None),
                'slots': getattr(tournament, 'max_participants', 0),
                'url': f'/tournaments/{tournament.slug}/' if tournament.slug else '/tournaments/',
                'is_live': is_tournament_live(tournament),
            }
    except Exception as e:
        print(f"Error fetching featured tournament: {e}")
    
    return None


def get_live_stats():
    """Get live platform statistics"""
    try:
        User = apps.get_model('auth', 'User')
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        
        return {
            'players': User.objects.count(),
            'tournaments': Tournament.objects.count(),
            'matches_today': 24,  # TODO: Implement actual match tracking
            'prize_distributed': '৳12,50,000',  # TODO: Calculate from payments
        }
    except Exception:
        return {
            'players': '12,500+',
            'tournaments': '150+',
            'matches_today': '24',
            'prize_distributed': '৳12,50,000',
        }


def get_game_tournament_count(game_slug):
    """Get active tournament count for a game"""
    try:
        Tournament = apps.get_model('tournaments', 'Tournament')
        count = Tournament.objects.filter(game__slug__iexact=game_slug).count()
        return count
    except Exception:
        return 0


def get_game_player_count(game_slug):
    """Get registered player count for a game"""
    try:
        Registration = apps.get_model('tournaments', 'Registration')
        count = Registration.objects.filter(
            tournament__game__slug__iexact=game_slug
        ).values('user').distinct().count()
        return count
    except Exception:
        return 0


def get_live_tournaments():
    """Get currently live tournaments"""
    try:
        Tournament = apps.get_model('tournaments', 'Tournament')
        now = timezone.now()
        
        tournaments = Tournament.objects.filter(
            tournament_start__lte=now,
            tournament_end__gte=now
        )[:3]
        
        return [{
            'name': t.name,
            'game': getattr(getattr(t, 'game', None), 'name', 'Unknown'),
            'players': getattr(t, 'max_participants', 0),
            'url': f'/tournaments/{t.slug}/' if t.slug else '/tournaments/',
        } for t in tournaments]
    except Exception:
        return []


def get_upcoming_events():
    """Get upcoming tournaments in next 7 days"""
    try:
        Tournament = apps.get_model('tournaments', 'Tournament')
        now = timezone.now()
        next_week = now + timedelta(days=7)
        
        tournaments = Tournament.objects.filter(
            tournament_start__gte=now,
            tournament_start__lte=next_week
        ).order_by('tournament_start')[:4]
        
        return [{
            'name': t.name,
            'game': getattr(getattr(t, 'game', None), 'name', 'Unknown'),
            'date': getattr(t, 'tournament_start', None),
            'prize': f"৳{t.prize_pool or 0:,}",
            'url': f'/tournaments/{t.slug}/' if t.slug else '/tournaments/',
        } for t in tournaments]
    except Exception:
        return []


def is_tournament_live(tournament):
    """Check if tournament is currently live"""
    try:
        now = timezone.now()
        start = getattr(tournament, 'tournament_start', None)
        end = getattr(tournament, 'tournament_end', None)
        if start and end:
            return start <= now <= end
    except Exception:
        pass
    return False