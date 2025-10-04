#!/usr/bin/env python
"""
Check tournament data completeness
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

def check_tournament_data(slug='efootball-champions'):
    """Check what data exists for a tournament"""
    
    t = Tournament.objects.select_related(
        'schedule', 'capacity', 'finance', 'rules', 'media', 'organizer', 'organizer__user'
    ).filter(slug=slug).first()
    
    if not t:
        print(f'❌ Tournament "{slug}" NOT FOUND')
        return
    
    print('='*60)
    print('TOURNAMENT DATA AUDIT')
    print('='*60)
    
    print('\n📋 BASIC INFO:')
    print(f'  Name: {t.name}')
    print(f'  Game: {t.game} ({t.get_game_display()})')
    print(f'  Status: {t.status} ({t.get_status_display()})')
    print(f'  Type: {t.tournament_type}')
    print(f'  Format: {t.format} ({t.get_format_display() if t.format else "MISSING"})')
    print(f'  Platform: {t.platform} ({t.get_platform_display() if t.platform else "MISSING"})')
    print(f'  Region: {t.region or "MISSING"}')
    print(f'  Language: {t.language}')
    print(f'  Registration Open: {t.registration_open}')
    
    print('\n📝 DESCRIPTIONS:')
    if t.short_description:
        print(f'  ✅ Short Description: {len(t.short_description)} chars')
        print(f'     Preview: {t.short_description[:80]}...')
    else:
        print('  ❌ Short Description: MISSING')
    
    if t.description:
        print(f'  ✅ Full Description: {len(t.description)} chars')
    else:
        print('  ❌ Full Description: MISSING')
    
    print('\n🖼️  BANNER/POSTER:')
    if t.banner:
        print(f'  ✅ Tournament Banner: {t.banner}')
    else:
        print('  ❌ Tournament Banner: MISSING')
    
    print('\n📅 SCHEDULE:')
    if hasattr(t, 'schedule') and t.schedule:
        print('  ✅ Schedule exists')
        print(f'     Registration Open: {t.schedule.reg_open_at or "MISSING"}')
        print(f'     Registration Close: {t.schedule.reg_close_at or "MISSING"}')
        print(f'     Tournament Start: {t.schedule.start_at or "MISSING"}')
        print(f'     Tournament End: {t.schedule.end_at or "MISSING"}')
        print(f'     Check-in Window: {t.schedule.check_in_window_text}')
        print(f'     Status: {t.schedule.registration_status}')
    else:
        print('  ❌ NO SCHEDULE DATA')
    
    print('\n👥 CAPACITY:')
    if hasattr(t, 'capacity') and t.capacity:
        print('  ✅ Capacity exists')
        print(f'     Max Teams: {t.capacity.max_teams}')
        print(f'     Current Registrations: {t.capacity.current_registrations}')
        print(f'     Available Slots: {t.capacity.available_slots}')
        print(f'     Team Size: {t.capacity.min_team_size}-{t.capacity.max_team_size} players')
        print(f'     Registration Mode: {t.capacity.registration_mode}')
        print(f'     Waitlist: {t.capacity.waitlist_enabled}')
        print(f'     Is Full: {t.capacity.is_full}')
    else:
        print('  ❌ NO CAPACITY DATA')
    
    print('\n💰 FINANCE:')
    if hasattr(t, 'finance') and t.finance:
        print('  ✅ Finance exists')
        print(f'     Prize Pool: ৳{t.finance.prize_pool_bdt:,.0f}')
        print(f'     Entry Fee: ৳{t.finance.entry_fee_bdt:,.0f}')
        if t.finance.prize_distribution:
            print(f'     Prize Distribution: {t.finance.prize_distribution}')
        else:
            print('     Prize Distribution: MISSING')
        if t.finance.refund_policy:
            print(f'     Refund Policy: {len(t.finance.refund_policy)} chars')
        else:
            print('     Refund Policy: MISSING')
    else:
        print('  ❌ NO FINANCE DATA')
    
    print('\n📜 RULES:')
    if hasattr(t, 'rules') and t.rules:
        print('  ✅ Rules exist')
        print(f'     General Rules: {len(t.rules.general_rules) if t.rules.general_rules else 0} chars')
        print(f'     Match Rules: {len(t.rules.match_rules) if t.rules.match_rules else 0} chars')
        print(f'     Eligibility: {len(t.rules.eligibility_requirements) if t.rules.eligibility_requirements else 0} chars')
        print(f'     Scoring System: {len(t.rules.scoring_system) if t.rules.scoring_system else 0} chars')
        print(f'     Penalty Rules: {len(t.rules.penalty_rules) if t.rules.penalty_rules else 0} chars')
    else:
        print('  ❌ NO RULES DATA')
    
    print('\n🎬 MEDIA:')
    if hasattr(t, 'media') and t.media:
        print('  ✅ Media exists')
        print(f'     Banner: {t.media.banner if t.media.banner else "MISSING"}')
        print(f'     Social Image: {t.media.social_media_image if t.media.social_media_image else "MISSING"}')
        print(f'     Rules PDF: {t.media.rules_pdf if t.media.rules_pdf else "MISSING"}')
        promo_count = t.media.promotional_images_count
        print(f'     Promo Images: {promo_count} uploaded')
    else:
        print('  ❌ NO MEDIA DATA')
    
    print('\n👤 ORGANIZER:')
    if t.organizer:
        print('  ✅ Organizer exists')
        print(f'     Username: {t.organizer.user.username}')
        print(f'     Email: {t.organizer.user.email}')
        print(f'     Avatar: {t.organizer.avatar if t.organizer.avatar else "MISSING"}')
    else:
        print('  ❌ NO ORGANIZER')
    
    print('\n' + '='*60)
    print('DATA COMPLETENESS SUMMARY')
    print('='*60)
    
    # Count what's complete
    complete = []
    incomplete = []
    
    if t.short_description: complete.append('Short Description')
    else: incomplete.append('Short Description')
    
    if t.description: complete.append('Full Description')
    else: incomplete.append('Full Description')
    
    if t.banner: complete.append('Banner')
    else: incomplete.append('Banner')
    
    if hasattr(t, 'schedule') and t.schedule: complete.append('Schedule')
    else: incomplete.append('Schedule')
    
    if hasattr(t, 'capacity') and t.capacity: complete.append('Capacity')
    else: incomplete.append('Capacity')
    
    if hasattr(t, 'finance') and t.finance: complete.append('Finance')
    else: incomplete.append('Finance')
    
    if hasattr(t, 'rules') and t.rules: complete.append('Rules')
    else: incomplete.append('Rules')
    
    if hasattr(t, 'media') and t.media: complete.append('Media')
    else: incomplete.append('Media')
    
    if t.organizer: complete.append('Organizer')
    else: incomplete.append('Organizer')
    
    print(f'\n✅ Complete ({len(complete)}/9):')
    for item in complete:
        print(f'   • {item}')
    
    if incomplete:
        print(f'\n❌ Incomplete ({len(incomplete)}/9):')
        for item in incomplete:
            print(f'   • {item}')
    
    print('\n' + '='*60)

if __name__ == '__main__':
    check_tournament_data()
