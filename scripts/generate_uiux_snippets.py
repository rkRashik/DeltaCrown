#!/usr/bin/env python
"""
UI/UX Phase B - Template Integration Helper
Generates template snippets for countdown timers and capacity tracking
"""

def generate_countdown_snippet(countdown_type, time_field, tournament_var="tournament"):
    """Generate countdown timer HTML snippet"""
    
    type_labels = {
        'registration-open': 'Registration Opening',
        'registration-close': 'Registration Closing',
        'tournament-start': 'Tournament Starting',
        'check-in-start': 'Check-in Opening',
        'check-in-end': 'Check-in Closing'
    }
    
    label = type_labels.get(countdown_type, 'Countdown')
    
    return f'''
<!-- {label} Countdown -->
{{% if {tournament_var}.{time_field} %}}
  <div class="countdown-timer" 
       data-countdown-type="{countdown_type}"
       data-target-time="{{{{ {tournament_var}.{time_field}|date:'c' }}}}"
       data-tournament-slug="{{{{ {tournament_var}.slug }}}}">
  </div>
{{% endif %}}
'''

def generate_capacity_snippet(capacity_var="capacity"):
    """Generate capacity tracking HTML snippet"""
    
    return f'''
<!-- Live Capacity Tracking -->
{{% if {capacity_var} %}}
  <div class="capacity-section">
    <h4>Capacity</h4>
    <div data-tournament-slots>
      {{{{ {capacity_var}.current_teams }}}}/{{{{ {capacity_var}.max_teams }}}}
    </div>
  </div>
{{% endif %}}
'''

def generate_full_sidebar_integration():
    """Generate complete Quick Facts sidebar with countdown and capacity"""
    
    return '''
<!-- Enhanced Quick Facts Sidebar -->
<div class="card">
  <h3 class="h3">Quick Facts</h3>
  
  <!-- Countdown Timer -->
  {% if schedule %}
    {% if schedule.registration_open_at and not tournament.registration_open %}
      <!-- Registration Not Yet Open -->
      <div class="countdown-timer" 
           data-countdown-type="registration-open"
           data-target-time="{{ schedule.registration_open_at|date:'c' }}"
           data-tournament-slug="{{ ctx.t.slug }}">
      </div>
    {% elif schedule.registration_close_at and tournament.registration_open and not tournament.has_started %}
      <!-- Registration Open - Show Closing Countdown -->
      <div class="countdown-timer" 
           data-countdown-type="registration-close"
           data-target-time="{{ schedule.registration_close_at|date:'c' }}"
           data-tournament-slug="{{ ctx.t.slug }}">
      </div>
    {% elif schedule.start_at and not tournament.has_started %}
      <!-- Registration Closed - Show Start Countdown -->
      <div class="countdown-timer" 
           data-countdown-type="tournament-start"
           data-target-time="{{ schedule.start_at|date:'c' }}"
           data-tournament-slug="{{ ctx.t.slug }}">
      </div>
    {% endif %}
  {% endif %}
  
  <dl class="meta compact">
    <!-- Schedule -->
    {% if schedule %}
      <div><dt>Starts</dt><dd>{{ schedule.start_at|date:"M j, H:i" }}</dd></div>
      <div><dt>Ends</dt><dd>{{ schedule.end_at|date:"M j, H:i" }}</dd></div>
      <div><dt>Reg. open</dt><dd>{{ schedule.registration_open_at|date:"M j, H:i" }}</dd></div>
      <div><dt>Reg. close</dt><dd>{{ schedule.registration_close_at|date:"M j, H:i" }}</dd></div>
    {% endif %}
    
    <!-- Format -->
    {% if ctx.format.type %}<div><dt>Format</dt><dd>{{ ctx.format.type|title }}</dd></div>{% endif %}
    {% if ctx.format.best_of %}<div><dt>Best of</dt><dd>Bo{{ ctx.format.best_of }}</dd></div>{% endif %}
    {% if ctx.platform %}<div><dt>Platform</dt><dd>{{ ctx.platform }}</dd></div>{% endif %}
    {% if ctx.region %}<div><dt>Region</dt><dd>{{ ctx.region }}</dd></div>{% endif %}
    
    <!-- Live Capacity (replaces static slots) -->
    {% if capacity %}
      <div>
        <dt>Capacity</dt>
        <dd data-tournament-slots>
          {{ capacity.current_teams }}/{{ capacity.max_teams }}
        </dd>
      </div>
    {% endif %}
  </dl>
</div>
'''

def generate_hero_card_integration():
    """Generate countdown for tournament hub hero card"""
    
    return '''
<!-- Tournament Hub - Featured Card with Countdown -->
<div class="hero-card">
  <div class="hc-top">
    <span class="live-dot"></span>
    Featured Tournament
  </div>
  
  <div class="hc-body">
    <!-- Tournament Info -->
    <a class="hc-banner" href="{{ t.dc_url }}">
      <img src="{{ t.dc_banner_url }}" alt="{{ t.dc_title }}">
    </a>
    <h3 class="hc-title"><a href="{{ t.dc_url }}">{{ t.dc_title }}</a></h3>
    
    <!-- Countdown Timer -->
    {% if t.schedule %}
      {% if not t.registration_open and t.schedule.registration_open_at %}
        <div class="countdown-timer" 
             data-countdown-type="registration-open"
             data-target-time="{{ t.schedule.registration_open_at|date:'c' }}"
             data-tournament-slug="{{ t.slug }}">
        </div>
      {% elif t.registration_open and not t.has_started and t.schedule.start_at %}
        <div class="countdown-timer" 
             data-countdown-type="tournament-start"
             data-target-time="{{ t.schedule.start_at|date:'c' }}"
             data-tournament-slug="{{ t.slug }}">
        </div>
      {% endif %}
    {% endif %}
    
    <!-- CTA Buttons -->
    <div class="hc-cta">
      <a class="cta-primary" href="{{ t.register_url }}">
        <i class="fa-solid fa-user-plus"></i> Join Now
      </a>
      <a class="cta-ghost" href="{{ t.dc_url }}">
        <i class="fa-solid fa-arrow-right"></i> Details
      </a>
    </div>
  </div>
</div>
'''

def generate_css_integration():
    """Generate CSS link tags for templates"""
    
    return '''
<!-- Add to {% block extra_head %} in tournament templates -->
<link rel="stylesheet" href="{% static 'siteui/css/countdown-timer.css' %}?v=1">
<link rel="stylesheet" href="{% static 'siteui/css/capacity-animations.css' %}?v=1">
'''

def generate_js_integration():
    """Generate JS script tags for templates"""
    
    return '''
<!-- Add to {% block extra_js %} in tournament templates -->
<script src="{% static 'js/countdown-timer.js' %}?v=1"></script>
<script src="{% static 'js/tournament-state-poller.js' %}?v=2"></script>
'''

def main():
    """Print all integration snippets"""
    
    print("=" * 80)
    print("UI/UX PHASE B - TEMPLATE INTEGRATION SNIPPETS")
    print("=" * 80)
    print()
    
    print("1. CSS INTEGRATION (Add to template head)")
    print("-" * 80)
    print(generate_css_integration())
    print()
    
    print("2. JAVASCRIPT INTEGRATION (Add to template footer)")
    print("-" * 80)
    print(generate_js_integration())
    print()
    
    print("3. COUNTDOWN SNIPPETS (Individual Use)")
    print("-" * 80)
    print("\nRegistration Opening:")
    print(generate_countdown_snippet('registration-open', 'schedule.registration_open_at'))
    print("\nRegistration Closing:")
    print(generate_countdown_snippet('registration-close', 'schedule.registration_close_at'))
    print("\nTournament Start:")
    print(generate_countdown_snippet('tournament-start', 'schedule.start_at'))
    print()
    
    print("4. CAPACITY SNIPPET (Individual Use)")
    print("-" * 80)
    print(generate_capacity_snippet())
    print()
    
    print("5. COMPLETE SIDEBAR INTEGRATION (tournament/detail.html)")
    print("-" * 80)
    print(generate_full_sidebar_integration())
    print()
    
    print("6. COMPLETE HERO CARD INTEGRATION (tournament/hub.html)")
    print("-" * 80)
    print(generate_hero_card_integration())
    print()
    
    print("=" * 80)
    print("INTEGRATION COMPLETE - Copy snippets to your templates")
    print("=" * 80)

if __name__ == '__main__':
    main()
