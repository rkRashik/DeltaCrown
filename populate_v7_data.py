#!/usr/bin/env python
"""
Populate V7 Template Data
Fixes data integration issues by populating missing fields
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament, TournamentMedia
from apps.user_profile.models import UserProfile

def populate_v7_data(slug='efootball-champions'):
    """Populate missing data for V7 template"""
    
    print('='*60)
    print('POPULATING V7 TEMPLATE DATA')
    print('='*60)
    
    # Get tournament
    try:
        t = Tournament.objects.select_related(
            'schedule', 'capacity', 'finance', 'rules', 'media', 'organizer'
        ).get(slug=slug)
        print(f'\n✅ Found tournament: {t.name}')
    except Tournament.DoesNotExist:
        print(f'\n❌ Tournament "{slug}" not found!')
        return
    
    changes_made = []
    
    # Fix 1: Tournament description
    if not t.description:
        t.description = """
<h2>About the Tournament</h2>
<p>Join the ultimate eFootball Mobile championship! Compete against the best players in Bangladesh for a chance to win ৳5,000 in prizes.</p>

<h3>What to Expect</h3>
<ul>
    <li><strong>Intense 1v1 Competition:</strong> Face off against skilled opponents in fast-paced matches</li>
    <li><strong>Fair Matchmaking:</strong> Balanced brackets ensure competitive gameplay</li>
    <li><strong>Verified Payouts:</strong> Instant prize distribution through secure payment methods</li>
    <li><strong>Professional Management:</strong> Experienced staff managing every aspect of the tournament</li>
    <li><strong>Live Support:</strong> Dedicated support team available throughout the event</li>
</ul>

<h3>Tournament Highlights</h3>
<p>This tournament features single-elimination format, ensuring every match counts. Players will compete in best-of-3 matches, with the winner advancing to the next round. The tournament culminates in an exciting grand final where the champion will be crowned.</p>

<h3>Why Participate?</h3>
<p>• Compete for a ৳5,000 prize pool<br>
• Gain recognition in the Bangladesh eFootball community<br>
• Test your skills against top players<br>
• Low entry fee of just ৳200<br>
• Experience professional tournament management</p>
"""
        changes_made.append('✅ Added full description')
    else:
        print('⏭️  Description already exists')
    
    # Fix 2: Tournament format
    if not t.format:
        t.format = 'SINGLE_ELIM'
        changes_made.append('✅ Set format to Single Elimination')
    else:
        print(f'⏭️  Format already set: {t.get_format_display()}')
    
    # Fix 3: Region
    if not t.region:
        t.region = 'Bangladesh'
        changes_made.append('✅ Set region to Bangladesh')
    else:
        print(f'⏭️  Region already set: {t.region}')
    
    # Save tournament changes
    if changes_made:
        t.save()
        print(f'\n📝 Tournament Updates:')
        for change in changes_made:
            print(f'   {change}')
    
    # Fix 4: Organizer
    if not t.organizer:
        # Try to find first available UserProfile
        organizer = UserProfile.objects.filter(user__is_staff=True).first()
        if not organizer:
            organizer = UserProfile.objects.first()
        
        if organizer:
            t.organizer = organizer
            t.save()
            print(f'\n✅ Assigned organizer: {organizer.user.username}')
        else:
            print('\n⚠️  Warning: No UserProfile found to assign as organizer')
            print('   Create a user first, then assign manually')
    else:
        print(f'\n⏭️  Organizer already assigned: {t.organizer.user.username}')
    
    # Fix 5: Create TournamentMedia if doesn't exist
    media, created = TournamentMedia.objects.get_or_create(tournament=t)
    if created:
        print('\n✅ Created TournamentMedia record')
        print('   Note: Banner and PDF uploads must be done via Django admin')
    else:
        print('\n⏭️  TournamentMedia record already exists')
        if not media.banner:
            print('   ⚠️  Banner not uploaded - upload via Django admin')
        if not media.rules_pdf:
            print('   ⚠️  Rules PDF not uploaded - upload via Django admin')
    
    # Fix 6: Prize distribution
    if not t.finance.prize_distribution or t.finance.prize_distribution == {}:
        # Calculate distribution from prize pool
        total_prize = float(t.finance.prize_pool_bdt)
        t.finance.prize_distribution = {
            "1st Place": total_prize * 0.50,  # 50%
            "2nd Place": total_prize * 0.30,  # 30%
            "3rd Place": total_prize * 0.20,  # 20%
        }
        t.finance.save()
        print('\n✅ Added prize distribution:')
        print(f'   • 1st Place: ৳{total_prize * 0.50:,.0f} (50%)')
        print(f'   • 2nd Place: ৳{total_prize * 0.30:,.0f} (30%)')
        print(f'   • 3rd Place: ৳{total_prize * 0.20:,.0f} (20%)')
    else:
        print('\n⏭️  Prize distribution already configured')
    
    # Fix 7: Rules content
    rules_updated = []
    
    if not t.rules.general_rules:
        t.rules.general_rules = """
<h3>🎮 General Tournament Rules</h3>
<ol>
    <li><strong>Registration:</strong> All participants must complete registration and payment before the deadline</li>
    <li><strong>Check-in:</strong> Mandatory check-in required 60 minutes before tournament start</li>
    <li><strong>Fair Play:</strong> No cheating, hacking, or exploitation of game bugs</li>
    <li><strong>Conduct:</strong> Respect all opponents, organizers, and staff</li>
    <li><strong>Communication:</strong> Participants must be available on designated communication channels</li>
    <li><strong>Punctuality:</strong> Be ready for your matches on time - defaults may be issued for no-shows</li>
</ol>
"""
        rules_updated.append('General Rules')
    
    if not t.rules.match_rules:
        t.rules.match_rules = """
<h3>⚽ Match Rules</h3>
<ul>
    <li><strong>Format:</strong> Single Elimination, Best of 3 (BO3)</li>
    <li><strong>Match Duration:</strong> 10 minutes per game</li>
    <li><strong>Default Win:</strong> If opponent doesn't show within 10 minutes of scheduled time</li>
    <li><strong>Connection Issues:</strong> Players responsible for stable internet connection</li>
    <li><strong>Disconnections:</strong> If disconnect occurs, match may be replayed at organizer's discretion</li>
    <li><strong>Result Reporting:</strong> Winner must report match result with screenshot proof</li>
    <li><strong>Disputes:</strong> Contact admin immediately if any issues arise</li>
</ul>
"""
        rules_updated.append('Match Rules')
    
    if not t.rules.eligibility_requirements:
        t.rules.eligibility_requirements = """
<h3>✅ Eligibility Requirements</h3>
<ul>
    <li><strong>Age:</strong> Must be 16 years or older to participate</li>
    <li><strong>Location:</strong> Open to players from Bangladesh</li>
    <li><strong>Account:</strong> Valid eFootball Mobile account required</li>
    <li><strong>Payment:</strong> Entry fee of ৳200 must be paid to confirm registration</li>
    <li><strong>Fair Play:</strong> Account must be in good standing (no bans or violations)</li>
    <li><strong>Multiple Accounts:</strong> One entry per person only</li>
</ul>
"""
        rules_updated.append('Eligibility Requirements')
    
    if not t.rules.scoring_system:
        t.rules.scoring_system = """
<h3>🏆 Scoring System</h3>
<ul>
    <li><strong>Match Format:</strong> Best of 3 - first to win 2 games advances</li>
    <li><strong>Tiebreaker:</strong> If needed, extra time and penalties follow eFootball rules</li>
    <li><strong>Points:</strong> 1 point per game win</li>
    <li><strong>Grand Final:</strong> Best of 5 (BO5) format</li>
    <li><strong>Winner Determination:</strong> Player/team with most round wins advances</li>
</ul>
"""
        rules_updated.append('Scoring System')
    
    if not t.rules.penalty_rules:
        t.rules.penalty_rules = """
<h3>⚠️ Penalties & Disqualification</h3>
<ul>
    <li><strong>Warning:</strong> First offense for minor violations</li>
    <li><strong>Game Loss:</strong> Awarded for repeated minor violations or moderate offenses</li>
    <li><strong>Match Loss:</strong> Awarded for serious violations</li>
    <li><strong>Disqualification:</strong> Immediate removal for:
        <ul>
            <li>Cheating or hacking</li>
            <li>Abusive behavior or harassment</li>
            <li>Match fixing or collusion</li>
            <li>Using unauthorized accounts</li>
        </ul>
    </li>
    <li><strong>No Refund:</strong> Disqualified players forfeit entry fee and prizes</li>
</ul>
"""
        rules_updated.append('Penalty Rules')
    
    if rules_updated:
        t.rules.save()
        print(f'\n✅ Added rules content:')
        for rule in rules_updated:
            print(f'   • {rule}')
    else:
        print('\n⏭️  Rules content already exists')
    
    # Fix 8: Refund policy
    if not t.finance.refund_policy:
        t.finance.refund_policy = """
Refund Policy:
- Full refund available up to 48 hours before tournament start
- 50% refund available up to 24 hours before tournament start
- No refunds within 24 hours of tournament start
- Refunds processed within 5-7 business days
- To request refund, contact support with your registration details
"""
        t.finance.save()
        print('\n✅ Added refund policy')
    else:
        print('\n⏭️  Refund policy already exists')
    
    print('\n' + '='*60)
    print('DATA POPULATION COMPLETE')
    print('='*60)
    print('\n📌 MANUAL STEPS REQUIRED:')
    print('   1. Upload banner image via Django admin:')
    print('      /admin/tournaments/tournamentmedia/')
    print('   2. (Optional) Upload rules PDF via Django admin')
    print('   3. Refresh tournament page to see changes')
    print(f'\n🔗 Tournament URL: http://127.0.0.1:8002/tournaments/{slug}/')
    print('='*60)

if __name__ == '__main__':
    populate_v7_data()
