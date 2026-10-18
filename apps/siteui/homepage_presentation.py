"""Shared desktop/mobile homepage copy derived from public state, without I/O."""


def get_homepage_presentation(stats, hero):
    count = stats.get('games_count', 0)
    open_count = stats.get('registration_open', 0)
    live_count = stats.get('tournaments_live', 0)
    if open_count:
        status = f'{open_count} tournament{"s" if open_count != 1 else ""} accepting entries'
    elif live_count:
        status = 'Tournaments live · registration currently closed'
    else:
        status = 'Explore teams and games · no open registrations'
    games_label = f'{count} supported game{"s" if count != 1 else ""}' if count else 'Explore supported games'
    summary = (
        'Join tournaments, build your squad, and rise from Rookie to The Crown'
        + (f' across {count} games, mobile to PC.' if count else ', mobile to PC.')
    )
    return {
        'games_count': count,
        'games_label': games_label,
        'status': status,
        'has_open_registration': bool(open_count),
        'summary': hero.get('subcopy') if hero.get('mode') != 'guest' else summary,
        'primary_url': hero['primary_cta_url'],
        'primary_label': hero['primary_cta_label'],
        'secondary_url': '/tournaments/' if hero.get('mode') == 'guest' and not open_count else hero['secondary_cta_url'],
        'secondary_label': 'Browse tournaments' if hero.get('mode') == 'guest' and not open_count else hero['secondary_cta_label'],
    }


def tournament_presentation(status, registration_end, now, full=False):
    can_register = status == 'registration_open' and not full and (
        registration_end is None or registration_end > now
    )
    if status == 'live':
        label = 'Live now'
    elif can_register:
        label = 'Registration open'
    elif full and status == 'registration_open':
        label = 'Entries full'
    elif status == 'published':
        label = 'Upcoming'
    else:
        label = 'Registration closed'
    return {
        'can_register': can_register,
        'status_label': label,
        'cta_label': 'Join tournament' if can_register else 'View tournament',
    }
