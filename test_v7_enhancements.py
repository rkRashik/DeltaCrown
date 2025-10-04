#!/usr/bin/env python
"""
Test V7 model enhancements
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

def test_enhancements(slug='efootball-champions'):
    """Test new model properties"""
    
    t = Tournament.objects.select_related(
        'schedule', 'capacity', 'finance', 'rules', 'media', 'organizer'
    ).get(slug=slug)
    
    print('='*60)
    print('V7 MODEL ENHANCEMENTS TEST')
    print('='*60)
    
    print('\n🎯 TOURNAMENT PROPERTIES:')
    print(f'  Registration Progress: {t.registration_progress_percentage:.1f}%')
    print(f'  Registration Status Badge: {t.registration_status_badge}')
    print(f'  Status Badge: {t.status_badge}')
    print(f'  Is Full: {t.is_full}')
    print(f'  Has Available Slots: {t.has_available_slots}')
    
    print('\n💰 FINANCE PROPERTIES:')
    print(f'  Prize Distribution Formatted: {len(t.finance.prize_distribution_formatted)} positions')
    for pos in t.finance.prize_distribution_formatted:
        print(f'    • {pos["position"]}: {pos["amount_formatted"]} ({pos["percentage"]}%)')
    print(f'  Total Prize Pool Formatted: {t.finance.total_prize_pool_formatted}')
    print(f'  Entry Fee Display: {t.finance.entry_fee_display}')
    
    print('\n📅 SCHEDULE PROPERTIES:')
    print(f'  Registration Countdown: {t.schedule.registration_countdown}')
    print(f'  Tournament Countdown: {t.schedule.tournament_countdown}')
    print(f'  Is Registration Closing Soon: {t.schedule.is_registration_closing_soon}')
    print(f'  Phase Status: {t.schedule.phase_status}')
    print(f'  Timeline Phases: {len(t.schedule.timeline_formatted)} phases')
    for phase in t.schedule.timeline_formatted:
        print(f'    • {phase["icon"]} {phase["phase"]} ({phase["status"]})')
    
    print('\n🎬 MEDIA PROPERTIES:')
    print(f'  Banner URL (or default): {t.media.banner_url_or_default}')
    print(f'  Thumbnail URL (or default): {t.media.thumbnail_url_or_default}')
    print(f'  Has Complete Media: {t.media.has_complete_media}')
    print(f'  Media Count: {t.media.media_count}')
    
    print('\n🔍 SEO META:')
    seo = t.seo_meta
    print(f'  Title: {seo["title"]}')
    print(f'  Description: {seo["description"][:80]}...')
    print(f'  Keywords: {seo["keywords"]}')
    print(f'  OG Image: {seo["og_image"]}')
    
    print('\n' + '='*60)
    print('✅ ALL PROPERTIES WORKING!')
    print('='*60)

if __name__ == '__main__':
    test_enhancements()
