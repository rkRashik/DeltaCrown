# 🎮 DeltaCrown Dynamic Form Builder - Complete Planning Specification

**Document Version:** 2.0  
**Date:** November 25, 2025  
**Status:** Planning Phase  
**Author:** DeltaCrown Development Team

---

## 🎯 Executive Summary

DeltaCrown is implementing a **revolutionary dynamic form builder system** for tournament registration, bringing the platform to 2025 industry standards. Instead of hard-coded forms, organizers can build custom registration experiences using a drag-and-drop interface similar to Google Forms/Typeform, but specialized for esports.

**Vision:** Every tournament gets a unique, professionally designed registration form tailored to its specific game, format, and requirements.

**Key Innovation:** Organizers choose from pre-built templates or create custom forms with toggle-able fields, dropdown configurations, and conditional logic—all without writing a single line of code.

---

## 📊 Current State vs Future State

### Current System (65% Complete)
- ❌ Hard-coded registration forms
- ❌ CustomField system (limited flexibility)
- ❌ One-size-fits-all wizard
- ✅ Payment verification workflow
- ✅ Service layer architecture

### Future System (Target)
- ✅ Dynamic form builder (organizer control)
- ✅ Pre-built game-specific templates
- ✅ Drag-and-drop field management
- ✅ Conditional logic support
- ✅ Auto-fill from user profiles
- ✅ Mobile-first responsive design
- ✅ Real-time form preview

---

## 🏗️ System Architecture

### Component Overview

```
┌────────────────────────────────────────────────────────────┐
│                  DYNAMIC FORM BUILDER SYSTEM               │
└────────────────────────────────────────────────────────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       │                       │
┌───▼────┐          ┌───────▼────────┐      ┌──────▼──────┐
│TEMPLATE│          │  FORM BUILDER  │      │   FORM      │
│LIBRARY │◄─────────┤  (Organizer)   │      │  RENDERER   │
│        │          │                │      │(Participant)│
└───┬────┘          └───────┬────────┘      └──────┬──────┘
    │                       │                      │
    │               ┌───────▼────────┐             │
    │               │ FIELD CONFIG   │             │
    │               │ & VALIDATION   │             │
    │               └───────┬────────┘             │
    │                       │                      │
    └───────────────────────┼──────────────────────┘
                            │
                     ┌──────▼──────┐
                     │ REGISTRATION│
                     │   STORAGE   │
                     │   (JSONB)   │
                     └─────────────┘
```

---

## 🗄️ Database Schema

### 1. RegistrationFormTemplate

Pre-built form templates for quick tournament setup.

```python
class RegistrationFormTemplate(models.Model):
    """System and user-created form templates"""
    
    # Metadata
    name = CharField(max_length=200)
    slug = SlugField(unique=True)
    description = TextField()
    
    # Classification
    participation_type = CharField(choices=[
        ('solo', 'Solo Player'),
        ('team', 'Team'),
        ('duo', 'Duo/Squad'),
    ])
    game = ForeignKey('Game', null=True, blank=True)
    
    # Form structure (JSONB)
    form_schema = JSONField(default=dict)
    
    # Metadata
    icon = CharField(max_length=50, blank=True)  # Emoji or icon class
    thumbnail = ImageField(upload_to='form_templates/', null=True)
    is_active = BooleanField(default=True)
    is_system_template = BooleanField(default=False)
    is_featured = BooleanField(default=False)
    
    # Usage stats
    usage_count = IntegerField(default=0)
    average_completion_rate = DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Creator
    created_by = ForeignKey(User, null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Tags for discovery
    tags = JSONField(default=list)  # ["valorant", "apac", "ranked"]
    
    class Meta:
        ordering = ['-is_featured', '-usage_count', 'name']
        indexes = [
            Index(fields=['participation_type', 'game']),
            Index(fields=['is_active', 'is_system_template']),
            GinIndex(fields=['tags']),
        ]
```

### 2. TournamentRegistrationForm

Organizer-customized form per tournament.

```python
class TournamentRegistrationForm(models.Model):
    """Per-tournament customized registration form"""
    
    tournament = OneToOneField('Tournament', on_delete=CASCADE, 
                               related_name='registration_form')
    
    # Template source
    based_on_template = ForeignKey('RegistrationFormTemplate', 
                                   null=True, blank=True, on_delete=SET_NULL)
    
    # Complete form structure (editable copy)
    form_schema = JSONField(default=dict)
    
    # Form behavior settings
    enable_multi_step = BooleanField(default=True)
    enable_autosave = BooleanField(default=True)
    enable_progress_bar = BooleanField(default=True)
    allow_edits_after_submit = BooleanField(default=False)
    require_email_verification = BooleanField(default=False)
    
    # Anti-spam
    enable_captcha = BooleanField(default=True)
    rate_limit_per_ip = IntegerField(default=5)  # Max submissions per hour
    
    # Confirmation settings
    success_message = TextField(blank=True)
    redirect_url = URLField(blank=True)
    send_confirmation_email = BooleanField(default=True)
    
    # Advanced features
    conditional_rules = JSONField(default=dict, blank=True)
    validation_rules = JSONField(default=dict, blank=True)
    
    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    updated_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    
    # Analytics
    total_views = IntegerField(default=0)
    total_starts = IntegerField(default=0)
    total_completions = IntegerField(default=0)
    
    @property
    def completion_rate(self):
        if self.total_starts == 0:
            return 0
        return (self.total_completions / self.total_starts) * 100
```

### 3. Form Schema Structure (JSONB)

```json
{
  "version": "2.0",
  "form_id": "valorant_solo_apac_2025",
  "form_name": "APAC Solo Valorant Registration",
  "settings": {
    "theme": "dark",
    "primary_color": "#FF4655",
    "show_section_numbers": true,
    "enable_keyboard_navigation": true
  },
  "sections": [
    {
      "id": "player_info",
      "title": "Player Information",
      "description": "Tell us about yourself",
      "icon": "👤",
      "order": 1,
      "collapsible": false,
      "fields": [
        {
          "id": "full_name",
          "type": "text",
          "label": "Full Name",
          "placeholder": "Enter your real name",
          "help_text": "This will appear on certificates",
          "required": true,
          "enabled": true,
          "auto_fill_from": "user.get_full_name",
          "validation": {
            "min_length": 3,
            "max_length": 100,
            "pattern": "^[a-zA-Z\\s]+$"
          },
          "order": 1
        },
        {
          "id": "display_name",
          "type": "text",
          "label": "Display Name (Nickname)",
          "placeholder": "RazorBlade",
          "help_text": "This name will appear in brackets & streams",
          "required": true,
          "enabled": true,
          "validation": {
            "min_length": 3,
            "max_length": 30
          },
          "order": 2
        },
        {
          "id": "age",
          "type": "number",
          "label": "Age",
          "help_text": "You must be 13+ to participate",
          "required": true,
          "enabled": true,
          "validation": {
            "min_value": 13,
            "max_value": 100
          },
          "order": 3
        },
        {
          "id": "country",
          "type": "dropdown",
          "label": "Country/Region",
          "required": true,
          "enabled": true,
          "options": [
            {"value": "bd", "label": "Bangladesh", "enabled": true},
            {"value": "in", "label": "India", "enabled": true},
            {"value": "pk", "label": "Pakistan", "enabled": true},
            {"value": "np", "label": "Nepal", "enabled": true}
          ],
          "default_value": "bd",
          "order": 4
        }
      ]
    },
    {
      "id": "game_details",
      "title": "Game Details",
      "description": "Your in-game information",
      "icon": "🎮",
      "order": 2,
      "fields": [
        {
          "id": "riot_id",
          "type": "riot_id",
          "label": "Riot ID (Valorant ID)",
          "placeholder": "Razor#BD01",
          "help_text": "Format: PlayerName#TAG",
          "required": true,
          "enabled": true,
          "auto_fill_from": "user.profile.riot_id",
          "validation": {
            "pattern": "^[a-zA-Z0-9]+#[a-zA-Z0-9]+$"
          },
          "order": 1
        },
        {
          "id": "platform_server",
          "type": "dropdown",
          "label": "Platform / Server",
          "required": true,
          "enabled": true,
          "options": [
            {"value": "apac", "label": "Asia-Pacific (APAC)", "enabled": true}
          ],
          "default_value": "apac",
          "order": 2
        },
        {
          "id": "rank",
          "type": "rank_selector",
          "label": "Current Rank (Optional)",
          "help_text": "Helps us with fair matchmaking",
          "required": false,
          "enabled": true,
          "game": "valorant",
          "options": [
            "Iron I", "Iron II", "Iron III",
            "Bronze I", "Bronze II", "Bronze III",
            "Silver I", "Silver II", "Silver III",
            "Gold I", "Gold II", "Gold III",
            "Platinum I", "Platinum II", "Platinum III",
            "Diamond I", "Diamond II", "Diamond III",
            "Ascendant I", "Ascendant II", "Ascendant III",
            "Immortal I", "Immortal II", "Immortal III",
            "Radiant"
          ],
          "default_value": "Silver III",
          "order": 3
        }
      ]
    },
    {
      "id": "contact_info",
      "title": "Contact Information",
      "description": "How can we reach you?",
      "icon": "📞",
      "order": 3,
      "fields": [
        {
          "id": "email",
          "type": "email",
          "label": "Email Address",
          "help_text": "We'll send match info here",
          "required": true,
          "enabled": true,
          "auto_fill_from": "user.email",
          "validation": {
            "domain_whitelist": []
          },
          "order": 1
        },
        {
          "id": "phone",
          "type": "phone",
          "label": "WhatsApp / Phone Number",
          "help_text": "For urgent match updates",
          "required": true,
          "enabled": true,
          "validation": {
            "country_code": "BD",
            "format": "E.164"
          },
          "order": 2
        },
        {
          "id": "discord",
          "type": "text",
          "label": "Discord Username",
          "placeholder": "Razor#1234",
          "required": true,
          "enabled": true,
          "auto_fill_from": "user.profile.discord_id",
          "validation": {
            "pattern": "^.+#[0-9]{4}$"
          },
          "order": 3
        },
        {
          "id": "preferred_contact",
          "type": "dropdown",
          "label": "Preferred Contact Method",
          "required": true,
          "enabled": true,
          "options": [
            {"value": "discord", "label": "Discord", "enabled": true},
            {"value": "whatsapp", "label": "WhatsApp", "enabled": true},
            {"value": "email", "label": "Email", "enabled": true}
          ],
          "default_value": "discord",
          "order": 4
        }
      ]
    }
  ],
  "confirmation": {
    "title": "Review & Accept Terms",
    "sections": ["player_info", "game_details", "contact_info"],
    "legal": {
      "id": "rules_acceptance",
      "type": "legal_consent",
      "label": "I have read and agree to the tournament rules",
      "required": true,
      "content_url": "/tournaments/{{tournament_slug}}/rules",
      "expandable": true
    }
  }
}
```

---

## 🎨 Field Type Library

### Basic Input Fields

#### 1. Short Text (`text`)
```json
{
  "type": "text",
  "validation": {
    "min_length": 3,
    "max_length": 100,
    "pattern": "regex",
    "case": "uppercase|lowercase|titlecase"
  }
}
```

#### 2. Long Text (`textarea`)
```json
{
  "type": "textarea",
  "validation": {
    "min_length": 10,
    "max_length": 1000,
    "rows": 4
  }
}
```

#### 3. Number (`number`)
```json
{
  "type": "number",
  "validation": {
    "min_value": 0,
    "max_value": 100,
    "step": 1,
    "decimal_places": 0
  }
}
```

#### 4. Email (`email`)
```json
{
  "type": "email",
  "validation": {
    "domain_whitelist": ["gmail.com", "yahoo.com"],
    "require_verification": true
  }
}
```

#### 5. Phone (`phone`)
```json
{
  "type": "phone",
  "validation": {
    "country_code": "BD",
    "format": "E.164",
    "allow_international": false
  }
}
```

### Selection Fields

#### 6. Dropdown (`dropdown`)
```json
{
  "type": "dropdown",
  "options": [
    {"value": "option1", "label": "Option 1", "enabled": true},
    {"value": "option2", "label": "Option 2", "enabled": false}
  ],
  "default_value": "option1",
  "searchable": true,
  "allow_custom": false
}
```

#### 7. Radio Buttons (`radio`)
```json
{
  "type": "radio",
  "options": [...],
  "layout": "vertical|horizontal|grid"
}
```

#### 8. Checkboxes (`checkbox_group`)
```json
{
  "type": "checkbox_group",
  "options": [...],
  "validation": {
    "min_selections": 1,
    "max_selections": 3
  }
}
```

### Game-Specific Fields

#### 9. Riot ID (`riot_id`)
```json
{
  "type": "riot_id",
  "games": ["valorant", "league_of_legends"],
  "validation": {
    "pattern": "^[a-zA-Z0-9]+#[a-zA-Z0-9]+$",
    "verify_exists": false
  }
}
```

#### 10. Rank Selector (`rank_selector`)
```json
{
  "type": "rank_selector",
  "game": "valorant",
  "show_icon": true,
  "options": "auto",  // Auto-load from game config
  "allow_unranked": true
}
```

#### 11. Platform/Server (`platform_selector`)
```json
{
  "type": "platform_selector",
  "game": "valorant",
  "multi_select": false,
  "options": "auto"  // Auto-load regions
}
```

### File Upload Fields

#### 12. File Upload (`file`)
```json
{
  "type": "file",
  "validation": {
    "allowed_extensions": ["jpg", "png", "pdf"],
    "max_size_mb": 5,
    "scan_virus": true
  }
}
```

#### 13. Image Upload (`image`)
```json
{
  "type": "image",
  "validation": {
    "max_width": 1920,
    "max_height": 1080,
    "max_size_mb": 2,
    "aspect_ratio": "16:9",
    "formats": ["jpg", "png", "webp"]
  },
  "preview": true,
  "crop": true
}
```

### Advanced Fields

#### 14. Date Picker (`date`)
```json
{
  "type": "date",
  "validation": {
    "min_date": "today",
    "max_date": "2025-12-31",
    "disable_weekends": false
  }
}
```

#### 15. Legal Consent (`legal_consent`)
```json
{
  "type": "legal_consent",
  "required": true,
  "content_url": "/terms",
  "expandable": true,
  "version": "1.0"
}
```

---

## ✨ Esports-Specific Enhancements

### 1. Team Roster Validator
```json
{
  "type": "team_roster",
  "min_players": 5,
  "max_players": 7,
  "require_substitutes": true,
  "fields_per_player": [
    {"id": "ign", "type": "text", "label": "In-Game Name"},
    {"id": "riot_id", "type": "riot_id", "label": "Riot ID"},
    {"id": "role", "type": "dropdown", "label": "Role", 
     "options": ["Duelist", "Controller", "Initiator", "Sentinel"]}
  ],
  "validation": {
    "unique_ids": true,
    "verify_all_active": true,
    "check_duplicate_registration": true
  }
}
```

### 2. Availability Calendar
```json
{
  "type": "availability_matrix",
  "label": "Match Availability",
  "dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
  "time_slots": ["10:00", "14:00", "18:00", "22:00"],
  "required_available": 2
}
```

### 3. Skill Assessment
```json
{
  "type": "skill_rating",
  "label": "Self-Rate Your Skills",
  "categories": [
    {"id": "aim", "label": "Aim"},
    {"id": "game_sense", "label": "Game Sense"},
    {"id": "communication", "label": "Communication"}
  ],
  "max_stars": 5
}
```

### 4. Previous Tournament History
```json
{
  "type": "tournament_history",
  "label": "Previous Tournaments",
  "auto_fill": true,
  "show_stats": true,
  "fields": [
    {"id": "tournament_name", "type": "text"},
    {"id": "placement", "type": "dropdown", 
     "options": ["Champion", "Runner-up", "Top 4", "Top 8", "Participant"]}
  ],
  "max_entries": 5
}
```

### 5. Stream/Content Creator Fields
```json
{
  "type": "creator_profile",
  "label": "Are you a content creator?",
  "optional": true,
  "fields": [
    {"id": "twitch", "type": "url", "label": "Twitch Channel"},
    {"id": "youtube", "type": "url", "label": "YouTube Channel"},
    {"id": "followers", "type": "number", "label": "Total Followers"}
  ]
}
```

### 6. Anti-Cheat Acknowledgment
```json
{
  "type": "anti_cheat_consent",
  "label": "Anti-Cheat Agreement",
  "required": true,
  "content": "I agree to install and run [Anti-Cheat Software] during matches",
  "software": "Vanguard",
  "verify_installation": false
}
```

---

## 🎯 Pre-Built Templates

### Template 1: Valorant Solo (Default)
- Player Info: Name, Age, Country
- Game Details: Riot ID, Server, Rank
- Contact: Email, Phone, Discord
- **3 sections, 11 fields, ~3 min completion**

### Template 2: Valorant Team (5v5)
- Team Info: Name, Tag, Logo
- Captain Info: Full contact details
- Roster: 5-7 players with role selection
- Team Discord Server
- **4 sections, 18 fields, ~8 min completion**

### Template 3: PUBG Mobile Solo
- Player Info: Name, Age, Device Type
- Game Details: PUBG ID, Server, Tier
- Contact: Phone (primary), Discord
- **3 sections, 9 fields, ~2 min completion**

### Template 4: Mobile Legends Team
- Team Info: Name, Logo
- Roster: 5 players + 2 subs
- Preferred Server
- Team Strategy (optional textarea)
- **4 sections, 15 fields, ~7 min completion**

### Template 5: CS2 Team (Competitive)
- Team Info: Name, Tag, Country
- Roster: 5 players with Steam IDs
- Anti-Cheat Consent
- Match Availability Calendar
- **5 sections, 20 fields, ~10 min completion**

### Template 6: Free Fire Squad
- Squad Info: Name, Captain
- 4 Players with Free Fire IDs
- Preferred Drop Zone (dropdown)
- Communication Language
- **3 sections, 12 fields, ~5 min completion**

---

## 🎨 Form Builder UI Design

### Organizer Dashboard

**URL:** `/organizer/tournaments/<slug>/registration-form`

**Three-Panel Layout:**

```
┌────────────────────────────────────────────────────────────┐
│ Registration Form Builder - [Tournament Name]              │
├─────────────┬────────────────────────────┬─────────────────┤
│  TEMPLATES  │     FORM CANVAS            │   FIELD CONFIG  │
│             │                            │                 │
│ 📋 Default  │  ┌──────────────────────┐  │  Selected Field │
│   Solo      │  │ Section 1            │  │                 │
│             │  │ Player Info          │  │  Label:         │
│ 👥 Default  │  │ ─────────────────── │  │  [In-Game Name] │
│   Team      │  │ [≡] Full Name *      │  │                 │
│             │  │ [≡] Display Name *   │  │  Required: ☑    │
│ ⚡ Quick    │  │ [≡] Age *            │  │  Enabled: ☑     │
│   Start     │  │ + Add Field          │  │                 │
│             │  └──────────────────────┘  │  Validation:    │
│ ────────    │                            │  Min: [3]       │
│             │  ┌──────────────────────┐  │  Max: [50]      │
│ COMPONENTS  │  │ Section 2            │  │                 │
│             │  │ Game Details         │  │  [Save Changes] │
│ ➕ Text     │  │ ─────────────────── │  │                 │
│ ➕ Email    │  │ [≡] Riot ID *        │  │                 │
│ ➕ Dropdown │  │ [≡] Server *         │  │                 │
│ ➕ File     │  │ [≡] Rank             │  │                 │
│ ➕ Riot ID  │  │ + Add Field          │  │                 │
│ ➕ Rank     │  └──────────────────────┘  │                 │
│             │                            │                 │
│             │  + Add Section             │                 │
└─────────────┴────────────────────────────┴─────────────────┘

[Preview Form]  [Save Draft]  [Publish Form]
```

### Key Features:
1. **Drag & Drop** - Reorder sections and fields
2. **Toggle Enable/Disable** - Gray out without deleting
3. **Live Preview** - See participant view instantly
4. **Template Import** - One-click apply
5. **Duplicate Detection** - Warn about similar fields
6. **Undo/Redo** - 20-step history

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Database & Backend**
- [ ] Create `RegistrationFormTemplate` model
- [ ] Create `TournamentRegistrationForm` model
- [ ] Define JSON Schema for `form_schema`
- [ ] Write validators for all field types
- [ ] Add GIN indexes on JSONB
- [ ] Create `FormBuilderService`
- [ ] Create `FormRenderService`
- [ ] Create `FormValidationService`

**Tests**
- [ ] Unit tests for schema validation
- [ ] Service layer tests
- [ ] JSON Schema compliance tests

### Phase 2: Form Builder UI (Week 3-4)
**Organizer Interface**
- [ ] Template library page
- [ ] Form builder canvas (drag-drop)
- [ ] Field configuration modals
- [ ] Section management
- [ ] Live preview pane
- [ ] Save/publish workflow

**Pre-built Templates**
- [ ] Create 6 default templates
- [ ] Template preview cards
- [ ] Template search/filter

### Phase 3: Form Renderer (Week 5)
**Participant Interface**
- [ ] Multi-step wizard layout
- [ ] Dynamic field components
- [ ] Client-side validation
- [ ] Auto-fill integration
- [ ] Progress tracking
- [ ] Draft save/resume

### Phase 4: Advanced Features (Week 6-7)
- [ ] Conditional logic engine
- [ ] Team roster validator
- [ ] Anti-cheat consent flows
- [ ] Availability calendar
- [ ] Analytics dashboard

### Phase 5: Testing & Launch (Week 8)
- [ ] E2E tests (Playwright)
- [ ] Beta testing with 5 organizers
- [ ] Performance optimization
- [ ] Mobile testing
- [ ] Documentation
- [ ] Public launch

---

## 📈 Success Metrics

### Organizer Metrics
- **Template Usage:** 80% use default templates
- **Form Completion Time:** <10 min to build form
- **Customization Rate:** 30% customize beyond templates

### Participant Metrics
- **Form Completion Rate:** >85% (vs current 65%)
- **Time to Register:** <5 min for solo, <10 min for team
- **Dropout Rate:** <15% (vs current 35%)
- **Mobile Completion:** >60% complete on mobile

### Platform Metrics
- **Support Tickets:** -50% registration-related
- **Organizer Satisfaction:** 4.5/5 stars
- **Feature Adoption:** 70% of new tournaments use builder

---

## 🎯 Competitive Advantages

### vs Toornament
- ❌ Toornament: Fixed registration forms
- ✅ DeltaCrown: Fully customizable

### vs Challengermode
- ❌ Challengermode: Basic form builder
- ✅ DeltaCrown: Game-specific components

### vs Battlefy
- ❌ Battlefy: No team roster validation
- ✅ DeltaCrown: Smart team validation

### vs Local Platforms
- ❌ Others: Hard-coded, developer-dependent
- ✅ DeltaCrown: Self-service, no-code

---

## 🔐 Security & Privacy

### Data Protection
- All JSONB fields encrypted at rest
- PII fields (email, phone) hashed in analytics
- GDPR-compliant data export
- Right to erasure (soft delete)

### Anti-Spam
- reCAPTCHA v3 integration
- Rate limiting (5 submissions/hour per IP)
- Duplicate registration detection
- Email verification for new accounts

### Fraud Prevention
- Device fingerprinting
- IP geolocation checks
- Suspicious pattern detection
- Manual review queue for flagged registrations

---

## 💡 Future Enhancements (Post-MVP)

### Phase 2 Features
1. **Form Templates Marketplace**
   - Community-contributed templates
   - Paid premium templates
   - Template ratings/reviews

2. **Multi-Language Support**
   - Bengali, Hindi, Urdu translations
   - Auto-detect user language
   - Form-level language overrides

3. **Advanced Conditional Logic**
   - Show/hide entire sections
   - Calculate field values
   - Multi-condition rules

4. **Integration APIs**
   - Discord bot auto-registration
   - Riot API verification
   - Steam ID validation

5. **White-Label Forms**
   - Custom branding per organizer
   - Remove DeltaCrown logo (premium)
   - Custom domains

### Phase 3 Features
6. **AI-Powered Form Optimization**
   - Suggest field improvements
   - Predict completion rates
   - Auto-remove unused fields

7. **Form Analytics Dashboard**
   - Field-level dropout analysis
   - Heatmaps (where users pause)
   - A/B testing support

8. **Blockchain Verification**
   - Store registrations on-chain
   - Tamper-proof records
   - NFT registration certificates

---

## 📚 Technical Standards

### JSON Schema Validation
All `form_schema` fields validate against JSON Schema Draft-07.

### API Versioning
Form builder API uses semantic versioning: `/api/v2/forms/`

### Performance Targets
- Form render: <500ms
- Builder load: <1s
- Auto-save: <200ms
- JSONB query: <50ms (with GIN index)

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader optimized
- High contrast mode

---

## 🎓 Documentation Requirements

### For Organizers
1. Video tutorial: "Build Your First Form (5 min)"
2. Written guide: Field type reference
3. Best practices: Optimal form design
4. FAQ: Common questions

### For Developers
1. API documentation (Swagger)
2. JSON Schema reference
3. Integration guide
4. Migration guide (CustomField → FormBuilder)

---

**END OF PLANNING SPECIFICATION**

*This document will be updated as development progresses.*
