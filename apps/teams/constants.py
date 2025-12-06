# apps/teams/constants.py
"""
Team Management Constants - Phase 1 & 2

Single source of truth for all team-related constants including:
- Validation rules (name, tag lengths, patterns)
- Roster limits
- Invite/cache timeouts
- Status choices
- Configuration values (Phase 2)
- Ranking constants (Phase 2)

Reference: 
- MASTER_IMPLEMENTATION_BACKLOG.md - Task 1.3 (Phase 1)
- MASTER_IMPLEMENTATION_BACKLOG_PART2.md - Task 5.1 (Phase 2)
"""
import re
from django.conf import settings

# ═══════════════════════════════════════════════════════════════════════════
# TEAM NAME VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

TEAM_NAME_MIN_LENGTH = 3
TEAM_NAME_MAX_LENGTH = 100
TEAM_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]{3,100}$')
TEAM_NAME_HELP_TEXT = "3-100 characters. Letters, numbers, spaces, hyphens, underscores allowed."

# ═══════════════════════════════════════════════════════════════════════════
# TEAM TAG VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

TEAM_TAG_MIN_LENGTH = 2
TEAM_TAG_MAX_LENGTH = 10
TEAM_TAG_PATTERN = re.compile(r'^[A-Z0-9]{2,10}$')
TEAM_TAG_HELP_TEXT = "2-10 uppercase letters and numbers only."

# ═══════════════════════════════════════════════════════════════════════════
# ROSTER LIMITS
# ═══════════════════════════════════════════════════════════════════════════

# Default roster sizes (can be overridden by game-specific config)
MIN_ROSTER_SIZE = 1
MAX_ROSTER_SIZE = 8
DEFAULT_ROSTER_SIZE = 5

# Substitute limits
MIN_SUBSTITUTES = 0
MAX_SUBSTITUTES = 2

# Total roster boundaries
ABSOLUTE_MIN_ROSTER = 1
ABSOLUTE_MAX_ROSTER = 50  # Hard limit across all games

# ═══════════════════════════════════════════════════════════════════════════
# INVITE & REQUEST SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

INVITE_EXPIRY_DAYS = 7
INVITE_EXPIRY_HOURS = 72  # Alternative specification
DRAFT_TTL_MINUTES = 30
TEAM_CACHE_TTL = 300  # 5 minutes in seconds

# ═══════════════════════════════════════════════════════════════════════════
# STATUS CHOICES
# ═══════════════════════════════════════════════════════════════════════════

# Team Membership Status
MEMBERSHIP_STATUS_ACTIVE = 'ACTIVE'
MEMBERSHIP_STATUS_INACTIVE = 'INACTIVE'
MEMBERSHIP_STATUS_SUSPENDED = 'SUSPENDED'
MEMBERSHIP_STATUS_BENCHED = 'BENCHED'

MEMBERSHIP_STATUS_CHOICES = [
    (MEMBERSHIP_STATUS_ACTIVE, 'Active'),
    (MEMBERSHIP_STATUS_INACTIVE, 'Inactive'),
    (MEMBERSHIP_STATUS_SUSPENDED, 'Suspended'),
    (MEMBERSHIP_STATUS_BENCHED, 'Benched'),
]

# Invite Status
INVITE_STATUS_PENDING = 'PENDING'
INVITE_STATUS_ACCEPTED = 'ACCEPTED'
INVITE_STATUS_DECLINED = 'DECLINED'
INVITE_STATUS_EXPIRED = 'EXPIRED'
INVITE_STATUS_CANCELLED = 'CANCELLED'

INVITE_STATUS_CHOICES = [
    (INVITE_STATUS_PENDING, 'Pending'),
    (INVITE_STATUS_ACCEPTED, 'Accepted'),
    (INVITE_STATUS_DECLINED, 'Declined'),
    (INVITE_STATUS_EXPIRED, 'Expired'),
    (INVITE_STATUS_CANCELLED, 'Cancelled'),
]

# Join Request Status
JOIN_REQUEST_STATUS_PENDING = 'PENDING'
JOIN_REQUEST_STATUS_APPROVED = 'APPROVED'
JOIN_REQUEST_STATUS_REJECTED = 'REJECTED'
JOIN_REQUEST_STATUS_CANCELLED = 'CANCELLED'

JOIN_REQUEST_STATUS_CHOICES = [
    (JOIN_REQUEST_STATUS_PENDING, 'Pending'),
    (JOIN_REQUEST_STATUS_APPROVED, 'Approved'),
    (JOIN_REQUEST_STATUS_REJECTED, 'Rejected'),
    (JOIN_REQUEST_STATUS_CANCELLED, 'Cancelled'),
]

# ═══════════════════════════════════════════════════════════════════════════
# ROLE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

# Team Management Roles (organizational hierarchy)
ROLE_OWNER = 'OWNER'  # Team captain/leader (NOTE: CAPTAIN deprecated, use OWNER)
ROLE_MANAGER = 'MANAGER'  # Team manager (Legacy)
ROLE_PLAYER = 'PLAYER'  # Regular player

# === PHASE 2 PROFESSIONAL ROLES (Task 6.2) ===

# Ownership & Management
ROLE_GENERAL_MANAGER = 'GENERAL_MANAGER'
ROLE_TEAM_MANAGER = 'TEAM_MANAGER'

# Coaching Staff
ROLE_HEAD_COACH = 'HEAD_COACH'
ROLE_ASSISTANT_COACH = 'ASSISTANT_COACH'
ROLE_PERFORMANCE_COACH = 'PERFORMANCE_COACH'

# Analysis & Strategy
ROLE_ANALYST = 'ANALYST'
ROLE_STRATEGIST = 'STRATEGIST'
ROLE_DATA_ANALYST = 'DATA_ANALYST'

# Support & Content
ROLE_CONTENT_CREATOR = 'CONTENT_CREATOR'
ROLE_SOCIAL_MEDIA_MANAGER = 'SOCIAL_MEDIA_MANAGER'
ROLE_COMMUNITY_MANAGER = 'COMMUNITY_MANAGER'

# === ROLE CATEGORIES (Task 6.2) ===

PLAYING_ROLES = [
    ROLE_PLAYER,
    'SUBSTITUTE',  # From model
]

COACHING_ROLES = [
    ROLE_HEAD_COACH,
    ROLE_ASSISTANT_COACH,
    ROLE_PERFORMANCE_COACH,
    ROLE_MANAGER,  # Legacy coach
]

MANAGEMENT_ROLES = [
    ROLE_OWNER,
    ROLE_GENERAL_MANAGER,
    ROLE_TEAM_MANAGER,
]

SUPPORT_ROLES = [
    ROLE_ANALYST,
    ROLE_STRATEGIST,
    ROLE_DATA_ANALYST,
    ROLE_CONTENT_CREATOR,
    ROLE_SOCIAL_MEDIA_MANAGER,
    ROLE_COMMUNITY_MANAGER,
]

# === PERMISSION GROUPS (Task 6.2) ===

# Roles that can edit team profile/settings
CAN_EDIT_TEAM = [
    ROLE_OWNER,
    ROLE_GENERAL_MANAGER,
    ROLE_TEAM_MANAGER,
]

# Roles that can manage roster
CAN_MANAGE_ROSTER = [
    ROLE_OWNER,
    ROLE_GENERAL_MANAGER,
    ROLE_HEAD_COACH,
]

# Roles that can manage content
CAN_MANAGE_CONTENT = [
    ROLE_OWNER,
    ROLE_SOCIAL_MEDIA_MANAGER,
    ROLE_CONTENT_CREATOR,
    ROLE_COMMUNITY_MANAGER,
]

# Roles that can view/edit strategy
CAN_ACCESS_STRATEGY = [
    ROLE_OWNER,
    ROLE_HEAD_COACH,
    ROLE_ASSISTANT_COACH,
    ROLE_ANALYST,
    ROLE_STRATEGIST,
]

# === ROLE LIMITS (Task 6.2) ===
MAX_OWNERS = 1
MAX_HEAD_COACHES = 1
MAX_GENERAL_MANAGERS = 1

TEAM_ROLE_CHOICES = [
    (ROLE_OWNER, 'Owner/Captain'),
    (ROLE_MANAGER, 'Manager'),
    (ROLE_PLAYER, 'Player'),
]

# Esports Player Roles (game-specific positions)
# These will eventually move to Game app configuration
PLAYER_ROLE_ENTRY = 'ENTRY'
PLAYER_ROLE_SUPPORT = 'SUPPORT'
PLAYER_ROLE_IGL = 'IGL'  # In-Game Leader
PLAYER_ROLE_FLEX = 'FLEX'
PLAYER_ROLE_AWP = 'AWP'

# ═══════════════════════════════════════════════════════════════════════════
# PERFORMANCE & LIMITS
# ═══════════════════════════════════════════════════════════════════════════

# Pagination
TEAMS_PER_PAGE = 20
MAX_SEARCH_RESULTS = 100

# Rate Limiting
MAX_INVITES_PER_DAY = 20
MAX_JOIN_REQUESTS_PER_DAY = 10
MAX_TEAM_CREATES_PER_USER = 5  # Lifetime limit per user

# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

# Error messages for consistent UX
ERROR_TEAM_NAME_REQUIRED = "Team name is required."
ERROR_TEAM_NAME_TOO_SHORT = f"Team name must be at least {TEAM_NAME_MIN_LENGTH} characters."
ERROR_TEAM_NAME_TOO_LONG = f"Team name cannot exceed {TEAM_NAME_MAX_LENGTH} characters."
ERROR_TEAM_NAME_INVALID_CHARS = "Team name contains invalid characters."
ERROR_TEAM_NAME_EXISTS = "A team with this name already exists."

ERROR_TEAM_TAG_REQUIRED = "Team tag is required."
ERROR_TEAM_TAG_TOO_SHORT = f"Team tag must be at least {TEAM_TAG_MIN_LENGTH} characters."
ERROR_TEAM_TAG_TOO_LONG = f"Team tag cannot exceed {TEAM_TAG_MAX_LENGTH} characters."
ERROR_TEAM_TAG_INVALID_FORMAT = "Team tag can only contain uppercase letters and numbers."
ERROR_TEAM_TAG_EXISTS = "A team with this tag already exists."

ERROR_ROSTER_FULL = "Team roster is full."
ERROR_ROSTER_TOO_SMALL = "Team must have at least {min_size} members."
ERROR_ALREADY_IN_TEAM = "User is already a member of this team."
ERROR_INVITE_EXPIRED = "This invitation has expired."
ERROR_NO_PERMISSION = "You don't have permission to perform this action."

# Success messages
SUCCESS_TEAM_CREATED = "Team '{name}' created successfully!"
SUCCESS_MEMBER_INVITED = "Invitation sent to {username}."
SUCCESS_MEMBER_JOINED = "{username} joined the team."
SUCCESS_MEMBER_REMOVED = "{username} removed from team."

# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2 CONFIGURATION (Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════

# Helper to get setting with default
def _get_teams_config(key, default):
    """Get configuration from settings.TEAMS_CONFIG with fallback to default."""
    return getattr(settings, 'TEAMS_CONFIG', {}).get(key, default)


# === INVITE SYSTEM (Extended) ===
MAX_PENDING_INVITES_PER_TEAM = _get_teams_config('MAX_PENDING_INVITES_PER_TEAM', 10)
MAX_PENDING_INVITES_PER_USER = _get_teams_config('MAX_PENDING_INVITES_PER_USER', 5)

# === JOIN REQUESTS ===
JOIN_REQUEST_EXPIRY_DAYS = _get_teams_config('JOIN_REQUEST_EXPIRY_DAYS', 14)
MAX_PENDING_JOIN_REQUESTS = _get_teams_config('MAX_PENDING_JOIN_REQUESTS', 20)

# === TEAM CREATION ===
MIN_TEAM_DESCRIPTION_LENGTH = 10
MAX_TEAM_DESCRIPTION_LENGTH = 2000

# === MEDIA UPLOADS ===
MAX_LOGO_SIZE_MB = _get_teams_config('MAX_LOGO_SIZE_MB', 5)
MAX_BANNER_SIZE_MB = _get_teams_config('MAX_BANNER_SIZE_MB', 10)
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'gif']

# === CACHE TTLs (Extended) ===
TEAM_LIST_CACHE_TTL = 180  # 3 minutes
STATS_CACHE_TTL = 600  # 10 minutes
RANKING_CACHE_TTL = 900  # 15 minutes

# === PAGINATION (Extended) ===
MEMBERS_PER_PAGE = 50
MATCHES_PER_PAGE = 15

# === ACTIVITY TRACKING ===
INACTIVE_THRESHOLD_DAYS = _get_teams_config('INACTIVE_THRESHOLD_DAYS', 90)
DISBANDED_AFTER_DAYS = _get_teams_config('DISBANDED_AFTER_DAYS', 180)

# === PERMISSIONS ===
OWNER_TRANSFER_COOLDOWN_DAYS = 7
KICK_COOLDOWN_HOURS = 24

# === NOTIFICATIONS ===
NOTIFY_CAPTAIN_ON_JOIN_REQUEST = True
NOTIFY_MEMBERS_ON_ROSTER_CHANGE = True
NOTIFY_ON_ACHIEVEMENT = True


# ═══════════════════════════════════════════════════════════════════════════
# RANKING CONSTANTS (Task 7.1)
# ═══════════════════════════════════════════════════════════════════════════

class RankingConstants:
    """Team ranking and ELO constants."""
    
    # === POINT MULTIPLIERS ===
    TOURNAMENT_WIN_MULTIPLIER = 1.5
    TOURNAMENT_RUNNER_UP_MULTIPLIER = 1.2
    TOURNAMENT_THIRD_PLACE_MULTIPLIER = 1.1
    TOURNAMENT_FOURTH_PLACE_MULTIPLIER = 1.05
    
    # === DECAY ===
    DECAY_RATE_PER_MONTH = 0.05  # 5% per month
    MAX_DECAY_PERCENTAGE = 0.5  # Max 50% total
    INACTIVITY_THRESHOLD_MONTHS = 1
    
    # === POINT CAPS ===
    MAX_ACHIEVEMENT_BONUS = 1000
    MAX_MEMBER_BONUS = 500
    
    # === ELO SYSTEM ===
    DEFAULT_ELO = 1500
    K_FACTOR = 32  # Standard K-factor for ELO calculations
    MIN_ELO = 0
    MAX_ELO = 3000
    
    # === DIVISIONS ===
    DIVISION_BRONZE = 'BRONZE'
    DIVISION_SILVER = 'SILVER'
    DIVISION_GOLD = 'GOLD'
    DIVISION_PLATINUM = 'PLATINUM'
    DIVISION_DIAMOND = 'DIAMOND'
    DIVISION_MASTER = 'MASTER'
    DIVISION_GRANDMASTER = 'GRANDMASTER'
    
    DIVISION_THRESHOLDS = {
        DIVISION_BRONZE: (0, 1199),
        DIVISION_SILVER: (1200, 1399),
        DIVISION_GOLD: (1400, 1599),
        DIVISION_PLATINUM: (1600, 1799),
        DIVISION_DIAMOND: (1800, 1999),
        DIVISION_MASTER: (2000, 2299),
        DIVISION_GRANDMASTER: (2300, 3000),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MATCH CONSTANTS (Task 5.1)
# ═══════════════════════════════════════════════════════════════════════════

class MatchConstants:
    """Match and tournament constants."""
    
    CHECK_IN_WINDOW_MINUTES = 30
    DEFAULT_MATCH_DURATION_MINUTES = 90
    FORFEIT_TIMEOUT_MINUTES = 15
    MAX_MATCH_RESCHEDULES = 2
