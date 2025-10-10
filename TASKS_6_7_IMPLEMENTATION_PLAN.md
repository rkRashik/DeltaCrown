# Tasks 6 & 7 Implementation Plan
**Date:** October 9, 2025  
**Status:** Planning Phase

---

## Overview

Building on the stable foundation of Tasks 1-5, we'll now implement:
- **Task 6:** Advanced Analytics & Reporting
- **Task 7:** Social & Community Integration

---

## Task 6: Advanced Analytics & Reporting

### 6.1 Team Performance Dashboard

#### Models to Create/Extend
```python
# apps/teams/models/analytics.py

class TeamStats(models.Model):
    """Comprehensive team statistics"""
    team = ForeignKey(Team)
    game = CharField(max_length=50)
    
    # Overall stats
    total_matches = PositiveIntegerField(default=0)
    matches_won = PositiveIntegerField(default=0)
    matches_lost = PositiveIntegerField(default=0)
    win_rate = DecimalField(max_digits=5, decimal_places=2)
    
    # Points tracking
    total_points = PositiveIntegerField(default=0)
    points_history = JSONField(default=list)  # [{date, points, change}]
    
    # Game-specific stats
    game_specific_stats = JSONField(default=dict)
    
    updated_at = DateTimeField(auto_now=True)

class PlayerStats(models.Model):
    """Individual player performance"""
    player = ForeignKey(UserProfile)
    team = ForeignKey(Team)
    game = CharField(max_length=50)
    
    # Participation
    tournaments_played = PositiveIntegerField(default=0)
    matches_played = PositiveIntegerField(default=0)
    attendance_rate = DecimalField(max_digits=5, decimal_places=2)
    
    # Performance
    mvp_count = PositiveIntegerField(default=0)
    contribution_score = DecimalField(max_digits=6, decimal_places=2)
    
    # Game-specific
    game_specific_stats = JSONField(default=dict)

class MatchRecord(models.Model):
    """Individual match history"""
    team = ForeignKey(Team)
    tournament = ForeignKey(Tournament, null=True)
    opponent_team = ForeignKey(Team, related_name='matches_against')
    
    match_date = DateTimeField()
    result = CharField(choices=[('win', 'Win'), ('loss', 'Loss'), ('draw', 'Draw')])
    score = CharField(max_length=50)  # "13-7", "2-1", etc.
    
    # Game-specific data
    game_specific_data = JSONField(default=dict)
    
    # Participating players
    participants = ManyToManyField(UserProfile, through='MatchParticipation')
```

#### Game-Specific Analytics Structure
```python
GAME_ANALYTICS_SCHEMAS = {
    'valorant': {
        'map_stats': {},  # {map_name: {wins, losses}}
        'agent_usage': {},  # {agent: usage_count}
        'rounds_won': 0,
        'rounds_lost': 0,
    },
    'cs2': {
        'map_stats': {},
        'role_performance': {},  # {role: {kills, deaths, assists}}
        'rounds_won': 0,
        'rounds_lost': 0,
    },
    'dota2': {
        'hero_usage': {},
        'role_stats': {},  # {role: {kda, wins}}
        'average_game_length': 0,
    },
    # ... etc
}
```

#### Views
```python
# apps/teams/views/analytics.py

class TeamAnalyticsDashboardView(LoginRequiredMixin, DetailView):
    """Main analytics dashboard"""
    
class TeamPerformanceAPIView(APIView):
    """AJAX endpoint for performance data"""
    
class ExportTeamStatsView(View):
    """Export stats as CSV"""
```

---

### 6.2 Graphical Reporting

#### Charts to Implement
1. **Points Progression** - Line chart (Chart.js)
2. **Role Performance** - Bar chart
3. **Player Contributions** - Pie chart
4. **Win Rate Over Time** - Line chart
5. **Game-Specific Stats** - Multi-series bar charts

#### Frontend Components
```javascript
// static/teams/js/analytics-dashboard.js

class AnalyticsDashboard {
    constructor(teamSlug) {
        this.teamSlug = teamSlug;
        this.charts = {};
    }
    
    async loadPointsProgression() {
        // Fetch data and render line chart
    }
    
    async loadRolePerformance() {
        // Fetch and render bar chart
    }
    
    async loadPlayerContributions() {
        // Fetch and render pie chart
    }
}
```

---

### 6.3 Admin Reports

#### Features
- Exportable CSVs for tournaments, points, achievements
- Filter by game, region, ranking
- Identify inactive/underperforming teams

#### Implementation
```python
# apps/teams/admin/analytics.py

class TeamStatsAdmin(admin.ModelAdmin):
    list_display = ['team', 'game', 'win_rate', 'total_matches']
    list_filter = ['game', 'updated_at']
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        # Generate CSV
```

---

## Task 7: Social & Community Integration

### 7.1 Team Chat/Messaging

#### Models
```python
# apps/teams/models/chat.py

class TeamChatMessage(models.Model):
    team = ForeignKey(Team)
    sender = ForeignKey(UserProfile)
    message = TextField()
    
    # Mentions
    mentions = ManyToManyField(UserProfile, related_name='chat_mentions')
    mention_type = CharField(choices=[
        ('all', 'All Members'),
        ('captains', 'Captains'),
        ('role', 'Specific Role'),
    ])
    
    # Attachments
    attachment = FileField(upload_to='team_chat/', blank=True)
    
    is_edited = BooleanField(default=False)
    is_deleted = BooleanField(default=False)
    
    created_at = DateTimeField(auto_now_add=True)
    edited_at = DateTimeField(null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at']),
        ]
```

#### Real-time Features
- WebSocket support (Django Channels) or
- AJAX polling for updates
- Notification on new messages

---

### 7.2 Discussion Board

#### Models
```python
# apps/teams/models/discussions.py

class TeamDiscussionPost(models.Model):
    team = ForeignKey(Team)
    author = ForeignKey(UserProfile)
    
    POST_TYPES = [
        ('discussion', 'Discussion'),
        ('announcement', 'Announcement'),
        ('strategy', 'Strategy'),
        ('question', 'Question'),
    ]
    
    post_type = CharField(max_length=20, choices=POST_TYPES)
    title = CharField(max_length=200)
    content = TextField()  # Markdown supported
    content_html = TextField()  # Rendered HTML
    
    # Privacy
    is_public = BooleanField(default=False)
    
    # Engagement
    views_count = PositiveIntegerField(default=0)
    likes = ManyToManyField(UserProfile, related_name='liked_discussions')
    
    # Pinning
    is_pinned = BooleanField(default=False)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class TeamDiscussionComment(models.Model):
    post = ForeignKey(TeamDiscussionPost, related_name='comments')
    author = ForeignKey(UserProfile)
    content = TextField()
    content_html = TextField()
    
    # Threading
    parent_comment = ForeignKey('self', null=True, related_name='replies')
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

---

### 7.3 Enhanced Social Media Integration

#### Models Extension
```python
# Add to Team model

class Team(models.Model):
    # ... existing fields ...
    
    # Social Media
    twitch_channel = URLField(blank=True)
    youtube_channel = URLField(blank=True)
    discord_server = URLField(blank=True)
    twitter_handle = CharField(max_length=50, blank=True)
    instagram_handle = CharField(max_length=50, blank=True)
    
    # Privacy toggles
    show_social_media_publicly = BooleanField(default=True)
    
    # Stream embeds
    enable_twitch_embed = BooleanField(default=False)
    enable_youtube_embed = BooleanField(default=False)
```

---

### 7.4 Team Activity Feed

#### Enhanced Activity Tracking
```python
# Extend existing TeamActivity model

class TeamActivity(models.Model):
    # ... existing fields ...
    
    ACTIVITY_TYPES = [
        # Existing
        ('team_created', 'Team Created'),
        ('member_joined', 'Member Joined'),
        ('member_left', 'Member Left'),
        ('achievement_earned', 'Achievement Earned'),
        
        # New for Task 7
        ('post_created', 'Discussion Post Created'),
        ('tournament_registered', 'Tournament Registered'),
        ('match_won', 'Match Won'),
        ('match_lost', 'Match Lost'),
        ('rank_improved', 'Rank Improved'),
        ('milestone_reached', 'Milestone Reached'),
    ]
```

---

## Implementation Order

### Phase 1: Models & Database (Day 1)
1. Create analytics models (TeamStats, PlayerStats, MatchRecord)
2. Create chat models (TeamChatMessage)
3. Create discussion models (TeamDiscussionPost, TeamDiscussionComment)
4. Generate migrations
5. Create admin interfaces

### Phase 2: Backend Services (Day 2)
1. Analytics calculation service
2. Stats aggregation service
3. CSV export service
4. Chat message service
5. Discussion post service

### Phase 3: API Endpoints (Day 3)
1. Analytics data endpoints
2. Chat CRUD endpoints
3. Discussion board endpoints
4. Activity feed endpoint

### Phase 4: Frontend - Analytics (Day 4)
1. Analytics dashboard template
2. Chart.js integration
3. AJAX data loading
4. Responsive design

### Phase 5: Frontend - Social (Day 5)
1. Chat interface
2. Discussion board UI
3. Activity feed widget
4. Real-time updates

### Phase 6: Testing & Polish (Day 6)
1. Unit tests
2. Integration tests
3. Performance optimization
4. Documentation

---

## File Structure

```
apps/teams/
├── models/
│   ├── analytics.py          [NEW - Task 6]
│   ├── chat.py                [NEW - Task 7]
│   └── discussions.py         [NEW - Task 7]
├── services/
│   ├── analytics_calculator.py     [NEW - Task 6]
│   ├── stats_aggregator.py         [NEW - Task 6]
│   └── discussion_service.py       [NEW - Task 7]
├── views/
│   ├── analytics.py           [NEW - Task 6]
│   ├── chat.py                [NEW - Task 7]
│   └── discussions.py         [NEW - Task 7]
├── admin/
│   ├── analytics.py           [NEW - Task 6]
│   └── discussions.py         [NEW - Task 7]
└── templates/teams/
    ├── analytics_dashboard.html    [NEW - Task 6]
    ├── team_chat.html             [NEW - Task 7]
    └── discussion_board.html      [NEW - Task 7]

static/teams/
├── js/
│   ├── analytics-dashboard.js     [NEW - Task 6]
│   ├── team-chat.js               [NEW - Task 7]
│   └── discussion-board.js        [NEW - Task 7]
└── css/
    ├── analytics-dashboard.css    [NEW - Task 6]
    ├── team-chat.css              [NEW - Task 7]
    └── discussion-board.css       [NEW - Task 7]
```

---

## Dependencies to Add

```python
# requirements.txt additions

# For charts and data visualization
pandas==2.0.0
matplotlib==3.7.0

# For markdown support in discussions
markdown==3.4.0
bleach==6.0.0  # For sanitizing HTML

# For real-time chat (optional)
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0

# For CSV exports
unicodecsv==0.14.1
```

---

## Configuration Updates

```python
# settings.py additions

INSTALLED_APPS += [
    'channels',  # If using WebSockets
]

# Channel layers for real-time chat
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Markdown settings
MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.fenced_code',
]
```

---

## Success Metrics

### Task 6 Success Criteria
- [ ] Analytics dashboard displays team performance
- [ ] Game-specific stats shown correctly
- [ ] Charts render and update dynamically
- [ ] Member activity tracked accurately
- [ ] Admin can export CSV reports
- [ ] Mobile-responsive design
- [ ] Performance: Dashboard loads < 2 seconds

### Task 7 Success Criteria
- [ ] Team chat functional with message history
- [ ] Discussion board allows posts and comments
- [ ] Markdown rendering works
- [ ] Social media links integrated
- [ ] Activity feed updates in real-time
- [ ] Notifications for new messages/posts
- [ ] Mobile-responsive design
- [ ] Permissions enforced correctly

---

## Estimated Timeline

- **Planning & Setup:** 0.5 days
- **Task 6 Implementation:** 3 days
- **Task 7 Implementation:** 2.5 days
- **Testing & Polish:** 1 day
- **Total:** ~7 days

---

## Next Steps

1. Review this plan
2. Confirm requirements
3. Begin Phase 1: Models & Database
4. Progressive implementation with testing

---

*Implementation Plan - Tasks 6 & 7*  
*Ready to begin implementation!* 🚀
