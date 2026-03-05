# Discord Integration Plan — TOC & Tournament Hub

> **Author:** TOC Engineering  
> **Date:** March 2026  
> **Status:** PLANNING  
> **Priority:** P2 → P1 (elevated due to user demand)

---

## 1. Executive Summary

Discord is the primary communication platform for esports communities in Bangladesh and globally. This document outlines a phased integration plan to deeply embed Discord into the DeltaCrown Tournament Operations Center (TOC) and Tournament Hub.

---

## 2. Current State

### What exists today:
- `Tournament.social_discord` — stores a Discord server invite URL (manual link)
- `TournamentLobby.discord_server_url` — stores Discord server URL per lobby
- `OrgTeam.discord_url` — team Discord invite link
- `OrgTeam.discord_webhook_url` — webhook URL for team notifications
- `OrgTeam.discord_guild_id` — Discord server (guild) ID
- `OrgTeam.discord_announcement_channel_id` — announcement channel ID
- Hub Resources tab shows Discord link as a clickable card

### What's missing:
- No Discord bot integration
- No automated notifications to Discord
- No auto voice/text channel creation
- No Discord role assignment for tournament participants
- No live brackets/standings embed posts

---

## 3. Implementation Phases

### Phase 1: Webhook Notifications (Sprint 6-7) — LOW EFFORT, HIGH VALUE

**Goal:** Auto-post tournament events to a Discord channel via webhook.

**TOC Settings additions:**
- `discord_webhook_url` field on Tournament model
- Webhook test button in TOC Settings
- Channel selection (via webhook — each webhook targets one channel)

**Events to post via webhook:**
| Event | Webhook Message |
|-------|----------------|
| Registration opens | "🎮 Registration is now OPEN for {tournament_name}! [Register →]" |
| Registration closes | "🔒 Registration closed. {count} teams registered." |
| Check-in opens | "✅ Check-in is OPEN! You have {minutes} minutes." |
| Bracket generated | "🏆 Bracket is live! [View bracket →]" |
| Match result | "Match #{id}: {team_a} vs {team_b} — Score: {score}" |
| Tournament completed | "🎉 {winner} wins {tournament_name}!" |
| Announcement | Forward TOC announcements to Discord |

**Implementation:**
```python
# apps/tournaments/services/discord_webhook.py
import httpx, json

class DiscordWebhookService:
    @staticmethod
    async def post(webhook_url: str, embed: dict):
        """Send a Discord embed message via webhook."""
        payload = {"embeds": [embed]}
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code == 204

    @classmethod
    def build_embed(cls, title, description, color=0x7C3AED, fields=None, url=None, thumbnail=None):
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "DeltaCrown Tournament Platform"},
        }
        if fields: embed["fields"] = fields
        if url: embed["url"] = url
        if thumbnail: embed["thumbnail"] = {"url": thumbnail}
        return embed
```

**Hook into existing TOC notification system:**
- `fire_auto_event()` in `notifications_service.py` already fires on bracket/checkin events
- Add Discord webhook dispatch alongside email/in-app notifications
- Configure per-tournament in TOC Settings → "Discord Webhook URL"

---

### Phase 2: Discord Bot (Sprint 8-10) — MEDIUM EFFORT

**Goal:** DeltaCrown Discord bot that lives in tournament Discord servers.

**Bot Capabilities:**
1. **Auto Role Assignment**
   - Participant role to registered players
   - Staff role to tournament staff
   - Remove roles when registration is cancelled
   
2. **Auto Channel Creation**
   - `#tournament-info` — read-only announcements
   - `#match-{id}` — per-match text channels
   - Voice channels per match (optional)
   
3. **Slash Commands**
   - `/bracket` — View current bracket
   - `/standings` — View group standings  
   - `/checkin` — Check-in via Discord
   - `/schedule` — View match schedule
   - `/score {team_a_score} {team_b_score}` — Report match score (staff only)

**Architecture:**
```
DeltaCrown API  ←→  Discord Bot (discord.py)  ←→  Discord API
      ↕                                              ↕
  PostgreSQL                                   Discord Servers
```

**Bot models:**
```python
class DiscordBotConfig(models.Model):
    tournament = models.OneToOneField(Tournament, on_delete=models.CASCADE)
    guild_id = models.CharField(max_length=20)  # Discord server ID
    bot_token_encrypted = models.TextField()  # Encrypted bot token
    announce_channel_id = models.CharField(max_length=20, blank=True)
    match_category_id = models.CharField(max_length=20, blank=True)
    participant_role_id = models.CharField(max_length=20, blank=True)
    staff_role_id = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=False)
```

---

### Phase 3: Discord Authentication (Sprint 11-12) — MEDIUM EFFORT

**Goal:** Allow players to link their Discord account and verify identity.

**Features:**
- "Link Discord" button in user profile settings
- OAuth2 flow: DeltaCrown → Discord → callback → store Discord user_id
- Auto-match Discord members to tournament registrations
- Discord username shown in TOC participant grid
- "Verified via Discord" badge

**Models:**
```python
# On UserProfile
discord_user_id = models.CharField(max_length=20, blank=True, unique=True)
discord_username = models.CharField(max_length=37, blank=True)
discord_linked_at = models.DateTimeField(null=True, blank=True)
```

---

### Phase 4: Live Spectator Integration (Sprint 13+) — HIGH EFFORT

**Goal:** Real-time bracket/match updates posted to Discord threads.

**Features:**
- Live score updates in Discord threads
- Bracket image auto-generated and posted after each round
- Stream go-live notifications with @everyone ping
- Post-match VOD links

---

## 4. Database Impact

### Phase 1 (Webhook only):
- Add `discord_webhook_url` to Tournament model (1 field, 1 migration)
- No new models needed

### Phase 2 (Bot):
- New `DiscordBotConfig` model  
- New `DiscordChannelMapping` model (match_id → channel_id)

### Phase 3 (Auth):
- Add Discord fields to UserProfile model

---

## 5. TOC UI Additions

### Phase 1 — Settings Tab:
1. **Discord Webhook URL** field (already planned)
2. **Test Webhook** button — sends a test embed
3. **Event Toggle Matrix** — which events trigger Discord posts

### Phase 2 — Sidebar:
1. **Discord** nav item under "Communication" section
2. Discord management dashboard:
   - Bot connection status
   - Channel mapping table
   - Role mapping table
   - Recent webhook deliveries log

---

## 6. Security Considerations

- Webhook URLs must be validated (must match `https://discord.com/api/webhooks/...`)
- Bot tokens must be encrypted at rest (Fernet or Django's `signing` module)
- OAuth2 state tokens for CSRF protection
- Rate limiting on webhook posts (max 30/min per webhook)
- Webhook failures should retry with exponential backoff (Celery task)

---

## 7. Estimated Timeline

| Phase | Effort | Sprints | Dependencies |
|-------|--------|---------|-------------|
| Phase 1: Webhooks | 3-5 days | Sprint 6-7 | Notification system (done) |
| Phase 2: Bot | 2-3 weeks | Sprint 8-10 | Phase 1, Discord Developer Portal |
| Phase 3: Auth | 1-2 weeks | Sprint 11-12 | Phase 2, OAuth2 app approval |
| Phase 4: Live | 1-2 weeks | Sprint 13+ | Phase 2, WebSocket infrastructure |

---

## 8. Quick Win: Webhook Implementation Checklist

- [x] Add `discord_webhook_url` field to Tournament model
- [x] Create `DiscordWebhookService` in `apps/tournaments/services/`
- [x] Add webhook URL field to TOC Settings → Social section
- [x] Add "Test Webhook" button in Settings UI
- [x] Wire `fire_auto_event()` to dispatch Discord webhooks
- [x] Add webhook delivery log (store last 50 deliveries)
- [x] Create Celery task for async webhook dispatch with retry
- [x] Game-colored embeds (use game's primary color as embed sidebar)
