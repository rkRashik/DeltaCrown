# Part 3: Smart Registration & Game Rules Design

**Document Purpose**: Design per-game configuration system and smart registration architecture for 11-game support.

**Created**: December 8, 2025  
**Scope**: Game rules abstraction, smart registration flows, service boundaries

---

## 1. Game Rules Layer

### 1.1 Problem Statement

**Current Challenges**:
- ❌ 7 hardcoded if-else checks for game identity fields (Riot ID, Steam ID, etc.)
- ❌ No support for game-specific scoring rules (K/D ratios, rounds won, goals scored)
- ❌ Tournament formats hardcoded (single/double elimination only)
- ❌ Adding new games requires code changes and deployment

**Target Solution**:
- ✅ Single Games app with database-driven configuration
- ✅ Game-agnostic tournament system (works for any configured game)
- ✅ Pluggable rules modules for game-specific logic
- ✅ Add new games via admin panel (no code deployment)

---

### 1.2 Game Configuration Architecture

#### Core Principle: Configuration Over Code

All game-specific behavior should be driven by database configuration, with optional pluggable rules modules for complex logic.

```
┌─────────────────────────────────────────────────────────────┐
│                     GAMES APP STRUCTURE                     │
├─────────────────────────────────────────────────────────────┤
│  Models:                                                    │
│   - Game                    (catalog: 11 games)             │
│   - GamePlayerIdentityConfig (identity fields per game)     │
│   - GameTournamentConfig     (formats, scoring)             │
│   - GameScoringRule          (how to calculate points)      │
│   - GameMatchResultSchema    (result structure)             │
│                                                             │
│  Services:                                                  │
│   - GameService              (get game metadata)            │
│   - GameRulesEngine          (compute scores, validate)     │
│   - GameValidationService    (validate identities)          │
│                                                             │
│  Rules Modules (Optional):                                 │
│   - valorant_rules.py        (Valorant-specific logic)      │
│   - csgo_rules.py            (CS2-specific logic)           │
│   - default_rules.py         (generic fallback)             │
└─────────────────────────────────────────────────────────────┘
```

---

### 1.3 Data Models

#### Model 1: Game (Catalog)

```python
class Game(models.Model):
    """
    Game catalog (11 games).
    Core game metadata.
    """
    name = models.CharField(max_length=100)  # "Valorant"
    slug = models.SlugField(unique=True)     # "valorant"
    logo = models.ImageField(upload_to='games/logos/')
    
    # Display
    description = models.TextField()
    official_website = models.URLField()
    is_active = models.BooleanField(default=True)
    
    # Team Requirements
    team_size_min = models.PositiveIntegerField(default=1)  # 1 for solo, 5 for Valorant
    team_size_max = models.PositiveIntegerField(default=1)  # 1 for solo, 5 for Valorant
    allows_substitutes = models.BooleanField(default=False)
    
    # Rules Module
    rules_module = models.CharField(
        max_length=100, 
        blank=True,
        help_text='Python module path: games.rules.valorant_rules'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Example Data**:
```python
Game.objects.create(
    name='Valorant',
    slug='valorant',
    team_size_min=5,
    team_size_max=5,
    allows_substitutes=True,
    rules_module='games.rules.valorant_rules'
)

Game.objects.create(
    name='PUBG Mobile',
    slug='pubg-mobile',
    team_size_min=4,
    team_size_max=4,
    allows_substitutes=False,
    rules_module='games.rules.pubg_rules'
)
```

---

#### Model 2: GamePlayerIdentityConfig

**Purpose**: Define which identity fields are required/validated per game.

```python
class GamePlayerIdentityConfig(models.Model):
    """
    Per-game player identity field configuration.
    Replaces hardcoded if-else checks.
    """
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='identity_configs')
    
    # Field Mapping
    field_name = models.CharField(
        max_length=50,
        help_text='UserProfile field name: riot_id, steam_id, pubg_mobile_id'
    )
    display_label = models.CharField(
        max_length=100,
        help_text='Human-readable label: "Riot ID", "Steam ID"'
    )
    
    # Validation
    validation_pattern = models.CharField(
        max_length=255,
        blank=True,
        help_text='Regex pattern: ^[\w]+#[\w]+$ for Riot ID'
    )
    validation_error_message = models.TextField(
        default='Invalid format',
        help_text='Error shown if validation fails'
    )
    
    # Requirements
    is_required = models.BooleanField(default=True)
    is_immutable = models.BooleanField(
        default=True,
        help_text='Lock field after verification (prevent changes)'
    )
    requires_verification = models.BooleanField(
        default=False,
        help_text='Require OAuth/API verification before tournament registration'
    )
    
    # Display
    placeholder = models.CharField(max_length=100, blank=True, help_text='Example: Player#1234')
    help_text = models.TextField(blank=True, help_text='Field description for users')
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = [('game', 'field_name')]
        ordering = ['display_order']
```

**Example Data**:
```python
# Valorant: Riot ID required
GamePlayerIdentityConfig.objects.create(
    game=valorant,
    field_name='riot_id',
    display_label='Riot ID',
    validation_pattern=r'^[\w]+#[\w]+$',
    validation_error_message='Format: Username#TAG (e.g., Player#1234)',
    is_required=True,
    is_immutable=True,
    requires_verification=True,
    placeholder='Player#1234',
    help_text='Your Riot Games account ID',
    display_order=1
)

# CS2: Steam ID required
GamePlayerIdentityConfig.objects.create(
    game=cs2,
    field_name='steam_id',
    display_label='Steam ID',
    validation_pattern=r'^\d{17}$',
    validation_error_message='Steam ID must be 17 digits',
    is_required=True,
    is_immutable=True,
    requires_verification=True,
    placeholder='76561198000000000',
    help_text='Your Steam account ID (17 digits)',
    display_order=1
)

# PUBG Mobile: PUBG ID required
GamePlayerIdentityConfig.objects.create(
    game=pubg,
    field_name='pubg_mobile_id',
    display_label='PUBG Mobile ID',
    validation_pattern=r'^\d{10}$',
    validation_error_message='PUBG ID must be 10 digits',
    is_required=True,
    is_immutable=True,
    placeholder='1234567890',
    help_text='Your PUBG Mobile numeric ID',
    display_order=1
)
```

**Benefits**:
- ✅ Adding new game requires only config (no code changes)
- ✅ Auto-generates registration form fields from config
- ✅ Validation rules per game (Riot ID format, Steam ID length)
- ✅ Field locking controlled per config

---

#### Model 3: GameTournamentConfig

**Purpose**: Define supported tournament formats and settings per game.

```python
class GameTournamentConfig(models.Model):
    """
    Tournament configuration options per game.
    Defines supported formats, scoring, match structures.
    """
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='tournament_configs')
    
    # Format Support
    format_type = models.CharField(
        max_length=50,
        choices=[
            ('SINGLE_ELIMINATION', 'Single Elimination'),
            ('DOUBLE_ELIMINATION', 'Double Elimination'),
            ('ROUND_ROBIN', 'Round Robin'),
            ('SWISS', 'Swiss System'),
            ('LEAGUE', 'League (Multi-Week)'),
        ]
    )
    is_supported = models.BooleanField(default=True)
    
    # Match Structure
    best_of_options = models.JSONField(
        default=list,
        help_text='Allowed BO values: [1, 3, 5] for BO1, BO3, BO5'
    )
    default_best_of = models.PositiveIntegerField(default=1)
    
    # Scoring
    scoring_type = models.CharField(
        max_length=50,
        choices=[
            ('WIN_LOSS', 'Win/Loss Only'),
            ('ROUNDS', 'Rounds Won (Valorant, CS2)'),
            ('KILLS', 'Kills (PUBG, Apex)'),
            ('GOALS', 'Goals (Rocket League, FIFA)'),
            ('CUSTOM', 'Custom Scoring'),
        ],
        default='WIN_LOSS'
    )
    
    # Result Schema
    result_schema = models.JSONField(
        default=dict,
        help_text='Match result structure: {"rounds": int, "kills": int, ...}'
    )
    
    # Time Settings
    default_match_duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text='Expected match duration (for scheduling)'
    )
    check_in_window_minutes = models.PositiveIntegerField(
        default=15,
        help_text='Check-in opens X minutes before match'
    )
    
    class Meta:
        unique_together = [('game', 'format_type')]
```

**Example Data**:
```python
# Valorant: Single Elimination, Rounds Scoring
GameTournamentConfig.objects.create(
    game=valorant,
    format_type='SINGLE_ELIMINATION',
    is_supported=True,
    best_of_options=[1, 3, 5],
    default_best_of=3,
    scoring_type='ROUNDS',
    result_schema={
        'team1_rounds': {'type': 'int', 'min': 0, 'max': 25, 'required': True},
        'team2_rounds': {'type': 'int', 'min': 0, 'max': 25, 'required': True},
        'map_name': {'type': 'string', 'required': False},
    },
    default_match_duration_minutes=90,
    check_in_window_minutes=15
)

# PUBG Mobile: Swiss System, Kills Scoring
GameTournamentConfig.objects.create(
    game=pubg,
    format_type='SWISS',
    is_supported=True,
    best_of_options=[1],
    default_best_of=1,
    scoring_type='KILLS',
    result_schema={
        'placement': {'type': 'int', 'min': 1, 'max': 16, 'required': True},
        'kills': {'type': 'int', 'min': 0, 'required': True},
        'survival_time': {'type': 'int', 'min': 0, 'required': False},
    },
    default_match_duration_minutes=30,
    check_in_window_minutes=10
)

# FIFA: League Format, Goals Scoring
GameTournamentConfig.objects.create(
    game=fifa,
    format_type='LEAGUE',
    is_supported=True,
    best_of_options=[1],
    default_best_of=1,
    scoring_type='GOALS',
    result_schema={
        'team1_goals': {'type': 'int', 'min': 0, 'required': True},
        'team2_goals': {'type': 'int', 'min': 0, 'required': True},
        'extra_time': {'type': 'bool', 'required': False},
        'penalties': {'type': 'bool', 'required': False},
    },
    default_match_duration_minutes=20,
    check_in_window_minutes=5
)
```

---

#### Model 4: GameScoringRule

**Purpose**: Define how to calculate points from match results (for formats like Swiss, Round Robin).

```python
class GameScoringRule(models.Model):
    """
    Scoring rules for calculating tournament points.
    Used in Swiss, Round Robin, League formats.
    """
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='scoring_rules')
    tournament_format = models.CharField(max_length=50)
    
    # Point Awards
    points_for_win = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    points_for_loss = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    points_for_draw = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    
    # Bonus Points (game-specific)
    bonus_rules = models.JSONField(
        default=dict,
        help_text='{"kill_bonus": 0.1, "placement_bonus": [10, 7, 5, 3, 1]}'
    )
    
    # Tiebreakers
    tiebreaker_order = models.JSONField(
        default=list,
        help_text='["head_to_head", "kill_difference", "total_kills"]'
    )
    
    class Meta:
        unique_together = [('game', 'tournament_format')]
```

**Example Data**:
```python
# PUBG Mobile: Swiss System Scoring
GameScoringRule.objects.create(
    game=pubg,
    tournament_format='SWISS',
    points_for_win=0,  # No win/loss in PUBG
    points_for_loss=0,
    points_for_draw=0,
    bonus_rules={
        'placement_bonus': [10, 7, 5, 4, 3, 2, 1, 0],  # Top 8 placements
        'kill_bonus': 1,  # 1 point per kill
    },
    tiebreaker_order=['total_points', 'total_kills', 'best_placement']
)

# Valorant: Round Robin Scoring
GameScoringRule.objects.create(
    game=valorant,
    tournament_format='ROUND_ROBIN',
    points_for_win=3,
    points_for_loss=0,
    points_for_draw=0,  # No draws in Valorant
    bonus_rules={
        'round_difference_bonus': 0.1,  # Bonus for round differential
    },
    tiebreaker_order=['head_to_head', 'round_difference', 'total_rounds_won']
)
```

---

### 1.4 Game Rules Engine

**Purpose**: Abstract interface for game-specific logic with fallback to config-driven defaults.

#### Architecture

```python
# games/services/game_rules_engine.py
from typing import Protocol, Dict, Any
from decimal import Decimal

class GameRulesInterface(Protocol):
    """
    Protocol (interface) that all game rules modules must implement.
    Allows type checking without inheritance.
    """
    
    def calculate_match_points(
        self, 
        result_data: Dict[str, Any], 
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """
        Calculate tournament points from match result.
        
        Args:
            result_data: Match result (e.g., {"team1_kills": 15, "placement": 3})
            tournament_format: SWISS, ROUND_ROBIN, etc.
        
        Returns:
            {"participant1_points": Decimal("12.5"), "participant2_points": ...}
        """
        ...
    
    def validate_match_result(
        self, 
        result_data: Dict[str, Any],
        tournament_config: 'GameTournamentConfig'
    ) -> tuple[bool, list[str]]:
        """
        Validate match result structure and values.
        
        Returns:
            (is_valid, error_messages)
        """
        ...
    
    def determine_winner(
        self,
        result_data: Dict[str, Any]
    ) -> int:
        """
        Determine winner from match result.
        
        Returns:
            1 (participant1 wins), 2 (participant2 wins), 0 (draw)
        """
        ...


class GameRulesEngine:
    """
    Main rules engine that loads per-game rules modules.
    Falls back to config-driven default rules if no custom module.
    """
    
    _rules_cache: Dict[str, GameRulesInterface] = {}
    
    @classmethod
    def get_rules(cls, game: Game) -> GameRulesInterface:
        """
        Get rules module for game.
        Uses cache to avoid repeated imports.
        """
        if game.slug in cls._rules_cache:
            return cls._rules_cache[game.slug]
        
        # Try loading custom rules module
        if game.rules_module:
            try:
                module = importlib.import_module(game.rules_module)
                rules_class = getattr(module, 'GameRules')
                cls._rules_cache[game.slug] = rules_class(game)
                return cls._rules_cache[game.slug]
            except (ImportError, AttributeError) as e:
                logger.warning(f'Failed to load rules module for {game.slug}: {e}')
        
        # Fallback: Default config-driven rules
        default_rules = DefaultGameRules(game)
        cls._rules_cache[game.slug] = default_rules
        return default_rules
    
    @classmethod
    def calculate_match_points(
        cls,
        game: Game,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """Calculate tournament points for match result."""
        rules = cls.get_rules(game)
        return rules.calculate_match_points(result_data, tournament_format)
    
    @classmethod
    def validate_match_result(
        cls,
        game: Game,
        result_data: Dict[str, Any],
        tournament_config: GameTournamentConfig
    ) -> tuple[bool, list[str]]:
        """Validate match result."""
        rules = cls.get_rules(game)
        return rules.validate_match_result(result_data, tournament_config)
```

---

#### Default Rules (Config-Driven)

```python
# games/rules/default_rules.py
class DefaultGameRules:
    """
    Default rules implementation driven by GameScoringRule config.
    Used when game has no custom rules module.
    """
    
    def __init__(self, game: Game):
        self.game = game
    
    def calculate_match_points(
        self,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """
        Calculate points based on GameScoringRule config.
        """
        # Get scoring rule for this format
        try:
            scoring_rule = GameScoringRule.objects.get(
                game=self.game,
                tournament_format=tournament_format
            )
        except GameScoringRule.DoesNotExist:
            # Fallback: Simple win/loss
            winner = self.determine_winner(result_data)
            return {
                'participant1_points': Decimal('3') if winner == 1 else Decimal('0'),
                'participant2_points': Decimal('3') if winner == 2 else Decimal('0'),
            }
        
        # Determine winner
        winner = self.determine_winner(result_data)
        
        # Base points
        if winner == 1:
            points1 = scoring_rule.points_for_win
            points2 = scoring_rule.points_for_loss
        elif winner == 2:
            points1 = scoring_rule.points_for_loss
            points2 = scoring_rule.points_for_win
        else:  # Draw
            points1 = scoring_rule.points_for_draw
            points2 = scoring_rule.points_for_draw
        
        # Apply bonus rules from config
        bonus1 = self._calculate_bonus(result_data, 'participant1', scoring_rule.bonus_rules)
        bonus2 = self._calculate_bonus(result_data, 'participant2', scoring_rule.bonus_rules)
        
        return {
            'participant1_points': points1 + bonus1,
            'participant2_points': points2 + bonus2,
        }
    
    def _calculate_bonus(
        self,
        result_data: Dict[str, Any],
        participant: str,
        bonus_rules: Dict[str, Any]
    ) -> Decimal:
        """Calculate bonus points from config rules."""
        bonus = Decimal('0')
        
        # Kill bonus (if configured)
        if 'kill_bonus' in bonus_rules and 'kills' in result_data:
            kills_key = f'{participant}_kills' if f'{participant}_kills' in result_data else 'kills'
            if kills_key in result_data:
                bonus += Decimal(str(result_data[kills_key])) * Decimal(str(bonus_rules['kill_bonus']))
        
        # Placement bonus (if configured)
        if 'placement_bonus' in bonus_rules and 'placement' in result_data:
            placement = result_data['placement']
            placement_table = bonus_rules['placement_bonus']
            if placement <= len(placement_table):
                bonus += Decimal(str(placement_table[placement - 1]))
        
        return bonus
    
    def validate_match_result(
        self,
        result_data: Dict[str, Any],
        tournament_config: GameTournamentConfig
    ) -> tuple[bool, list[str]]:
        """
        Validate result against tournament_config.result_schema.
        """
        errors = []
        schema = tournament_config.result_schema
        
        for field_name, field_config in schema.items():
            # Required field check
            if field_config.get('required', False) and field_name not in result_data:
                errors.append(f'Missing required field: {field_name}')
                continue
            
            if field_name not in result_data:
                continue  # Optional field, skip
            
            value = result_data[field_name]
            
            # Type validation
            expected_type = field_config.get('type', 'string')
            if expected_type == 'int' and not isinstance(value, int):
                errors.append(f'{field_name} must be an integer')
            elif expected_type == 'string' and not isinstance(value, str):
                errors.append(f'{field_name} must be a string')
            elif expected_type == 'bool' and not isinstance(value, bool):
                errors.append(f'{field_name} must be a boolean')
            
            # Range validation (for int fields)
            if expected_type == 'int':
                if 'min' in field_config and value < field_config['min']:
                    errors.append(f'{field_name} must be >= {field_config["min"]}')
                if 'max' in field_config and value > field_config['max']:
                    errors.append(f'{field_name} must be <= {field_config["max"]}')
        
        return (len(errors) == 0, errors)
    
    def determine_winner(self, result_data: Dict[str, Any]) -> int:
        """
        Determine winner from result data.
        Generic logic: Compare score fields (rounds, kills, goals).
        """
        # Common patterns
        if 'team1_rounds' in result_data and 'team2_rounds' in result_data:
            if result_data['team1_rounds'] > result_data['team2_rounds']:
                return 1
            elif result_data['team2_rounds'] > result_data['team1_rounds']:
                return 2
            return 0  # Draw
        
        if 'team1_goals' in result_data and 'team2_goals' in result_data:
            if result_data['team1_goals'] > result_data['team2_goals']:
                return 1
            elif result_data['team2_goals'] > result_data['team1_goals']:
                return 2
            return 0  # Draw
        
        # Fallback: Check 'winner' field if present
        if 'winner' in result_data:
            return result_data['winner']
        
        # Cannot determine
        raise ValueError('Cannot determine winner from result data')
```

---

#### Custom Rules Example (Valorant)

```python
# games/rules/valorant_rules.py
class GameRules:
    """
    Valorant-specific rules.
    Handles rounds, spike plants, overtime logic.
    """
    
    def __init__(self, game: Game):
        self.game = game
    
    def calculate_match_points(
        self,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """
        Valorant uses simple win/loss (no bonus points).
        But we track round differential for tiebreakers.
        """
        winner = self.determine_winner(result_data)
        
        if tournament_format == 'ROUND_ROBIN':
            # Track round differential
            round_diff = result_data['team1_rounds'] - result_data['team2_rounds']
            
            return {
                'participant1_points': Decimal('3') if winner == 1 else Decimal('0'),
                'participant2_points': Decimal('3') if winner == 2 else Decimal('0'),
                'participant1_round_diff': round_diff,
                'participant2_round_diff': -round_diff,
            }
        
        # Default: Single Elimination (win/loss only)
        return {
            'participant1_points': Decimal('1') if winner == 1 else Decimal('0'),
            'participant2_points': Decimal('1') if winner == 2 else Decimal('0'),
        }
    
    def validate_match_result(
        self,
        result_data: Dict[str, Any],
        tournament_config: GameTournamentConfig
    ) -> tuple[bool, list[str]]:
        """
        Valorant-specific validation.
        """
        errors = []
        
        # Required fields
        if 'team1_rounds' not in result_data or 'team2_rounds' not in result_data:
            errors.append('Missing team rounds')
            return (False, errors)
        
        team1_rounds = result_data['team1_rounds']
        team2_rounds = result_data['team2_rounds']
        
        # Rounds must be 0-25
        if not (0 <= team1_rounds <= 25):
            errors.append('Team 1 rounds must be 0-25')
        if not (0 <= team2_rounds <= 25):
            errors.append('Team 2 rounds must be 0-25')
        
        # Winner must have reached 13 rounds (or won in overtime)
        max_rounds = max(team1_rounds, team2_rounds)
        if max_rounds < 13:
            errors.append('Winner must have at least 13 rounds')
        
        # Overtime logic: If score is 12-12, can go to 13-12, 14-12, etc.
        # But differential can only be 1 or 2 (13-11 normal, 14-12 overtime)
        if max_rounds >= 13:
            diff = abs(team1_rounds - team2_rounds)
            if diff == 0:
                errors.append('No draws in Valorant (someone must win)')
            # Allow overtime scores (can go 15-13, 16-14, etc.)
        
        return (len(errors) == 0, errors)
    
    def determine_winner(self, result_data: Dict[str, Any]) -> int:
        """Winner is whoever has more rounds."""
        if result_data['team1_rounds'] > result_data['team2_rounds']:
            return 1
        elif result_data['team2_rounds'] > result_data['team1_rounds']:
            return 2
        return 0  # Should not happen (validation prevents)
```

---

### 1.5 Using Game Rules Engine

#### Example 1: Validate Match Result Submission

```python
# tournaments/services/match_service.py
from games.services.game_rules_engine import GameRulesEngine

class MatchService:
    @staticmethod
    def submit_match_result(match_id: int, result_data: dict) -> Match:
        match = Match.objects.select_related('tournament__game').get(id=match_id)
        tournament = match.tournament
        game = tournament.game
        
        # Get tournament config
        tournament_config = GameTournamentConfig.objects.get(
            game=game,
            format_type=tournament.format
        )
        
        # Validate result using game rules
        is_valid, errors = GameRulesEngine.validate_match_result(
            game=game,
            result_data=result_data,
            tournament_config=tournament_config
        )
        
        if not is_valid:
            raise ValidationError(errors)
        
        # Determine winner
        winner = GameRulesEngine.get_rules(game).determine_winner(result_data)
        
        # Store result
        match.result_data = result_data  # JSONB field
        match.winner_participant = winner
        match.state = Match.PENDING_RESULT
        match.save()
        
        return match
```

---

#### Example 2: Calculate Tournament Points (Swiss/Round Robin)

```python
# tournaments/services/standings_service.py
class StandingsService:
    @staticmethod
    def update_standings(tournament_id: int):
        tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        game = tournament.game
        
        # Get all completed matches
        matches = Match.objects.filter(
            tournament=tournament,
            state=Match.COMPLETED
        )
        
        # Calculate points for each participant
        participant_points = defaultdict(Decimal)
        
        for match in matches:
            # Calculate points using game rules
            points = GameRulesEngine.calculate_match_points(
                game=game,
                result_data=match.result_data,
                tournament_format=tournament.format
            )
            
            participant_points[match.participant1_id] += points['participant1_points']
            participant_points[match.participant2_id] += points['participant2_points']
        
        # Update standings
        for participant_id, points in participant_points.items():
            Standing.objects.update_or_create(
                tournament=tournament,
                participant_id=participant_id,
                defaults={'points': points}
            )
```

---

### 1.6 Expanded Game Rules: Complex Scoring Systems

#### 1.6.1 Group-Based Scoring

**Use Case**: Group Stage tournaments where participants accumulate points across multiple matches before advancing to knockout rounds.

**Configuration**:

```python
# Model Enhancement
class GameTournamentConfig(models.Model):
    # ... existing fields ...
    
    supports_group_stage = models.BooleanField(default=False)
    group_stage_scoring_type = models.CharField(
        max_length=50,
        choices=[
            ('WIN_LOSS', 'Win/Loss Points'),
            ('ROUND_DIFFERENTIAL', 'Round Differential'),
            ('GOALS_DIFFERENCE', 'Goals Difference'),
            ('PLACEMENT_KILLS', 'Placement + Kills (PUBG)'),
        ],
        blank=True
    )
    group_advancement_rules = models.JSONField(
        default=dict,
        help_text='{"top_n_per_group": 2, "tiebreaker": ["head_to_head", "goal_diff"]}'
    )
```

**Example: Valorant Group Stage**

```python
# Group Stage Scoring Configuration
GameScoringRule.objects.create(
    game=valorant,
    tournament_format='GROUP_STAGE',
    points_for_win=3,
    points_for_loss=0,
    points_for_draw=0,
    bonus_rules={
        'round_differential': True,  # Track round differential as tiebreaker
        'rounds_per_win': 0.1,  # Bonus: 0.1 points per round won
    },
    tiebreaker_order=[
        'head_to_head',           # 1. Direct match result
        'round_difference',       # 2. Total rounds won - rounds lost
        'total_rounds_won',       # 3. Total rounds won
        'earliest_win',           # 4. Who achieved record first
    ]
)

# Group Stage Standings Calculation
class GroupStageStandingsService:
    @staticmethod
    def calculate_standings(group_id: int) -> List[Dict]:
        """
        Calculate group stage standings with tiebreakers.
        
        Returns ordered list:
        [
            {
                'participant': Team object,
                'matches_played': 6,
                'wins': 4,
                'losses': 2,
                'points': 12,
                'round_difference': +15,
                'rank': 1
            },
            ...
        ]
        """
        group = TournamentGroup.objects.get(id=group_id)
        matches = Match.objects.filter(group=group, state=Match.COMPLETED)
        
        # Accumulate stats
        stats = defaultdict(lambda: {
            'matches_played': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'points': 0,
            'rounds_won': 0,
            'rounds_lost': 0,
            'round_difference': 0,
        })
        
        for match in matches:
            p1_id = match.participant1_id
            p2_id = match.participant2_id
            
            # Get points from rules engine
            points = GameRulesEngine.calculate_match_points(
                game=group.tournament.game,
                result_data=match.result_data,
                tournament_format='GROUP_STAGE'
            )
            
            stats[p1_id]['matches_played'] += 1
            stats[p2_id]['matches_played'] += 1
            
            stats[p1_id]['points'] += points['participant1_points']
            stats[p2_id]['points'] += points['participant2_points']
            
            # Track rounds for tiebreakers
            if 'team1_rounds' in match.result_data:
                r1 = match.result_data['team1_rounds']
                r2 = match.result_data['team2_rounds']
                
                stats[p1_id]['rounds_won'] += r1
                stats[p1_id]['rounds_lost'] += r2
                stats[p2_id]['rounds_won'] += r2
                stats[p2_id]['rounds_lost'] += r1
                
                if r1 > r2:
                    stats[p1_id]['wins'] += 1
                    stats[p2_id]['losses'] += 1
                else:
                    stats[p2_id]['wins'] += 1
                    stats[p1_id]['losses'] += 1
        
        # Calculate round differential
        for participant_id in stats:
            stats[participant_id]['round_difference'] = (
                stats[participant_id]['rounds_won'] - 
                stats[participant_id]['rounds_lost']
            )
        
        # Sort by tiebreakers
        sorted_standings = sorted(
            stats.items(),
            key=lambda x: (
                -x[1]['points'],              # Primary: Most points
                -x[1]['round_difference'],    # Tiebreaker 1: Round diff
                -x[1]['rounds_won'],          # Tiebreaker 2: Total rounds
            )
        )
        
        # Assign ranks
        standings = []
        for rank, (participant_id, data) in enumerate(sorted_standings, start=1):
            standings.append({
                'participant_id': participant_id,
                'rank': rank,
                **data
            })
        
        return standings
```

---

#### 1.6.2 Swiss System Rounds

**Use Case**: Swiss System tournaments where participants play N rounds, paired against opponents with similar records each round.

**Configuration**:

```python
class GameTournamentConfig(models.Model):
    # ... existing fields ...
    
    supports_swiss = models.BooleanField(default=False)
    swiss_rounds_default = models.PositiveIntegerField(
        default=5,
        help_text='Default number of Swiss rounds (usually 5-7)'
    )
    swiss_pairing_method = models.CharField(
        max_length=50,
        choices=[
            ('DUTCH', 'Dutch System (record-based pairing)'),
            ('ACCELERATED', 'Accelerated Pairing (3-point head start for top seeds)'),
            ('MONRAD', 'Monrad System (random within record groups)'),
        ],
        default='DUTCH'
    )
```

**Swiss Round Pairing Logic**:

```python
# tournament_ops/services/swiss_pairing_service.py
class SwissPairingService:
    """
    Generate Swiss pairings each round.
    
    Dutch System:
    1. Sort participants by current record (wins-losses)
    2. Group participants by same record (3-0, 2-1, 1-2, 0-3)
    3. Within each record group, pair top-half vs bottom-half
    4. Avoid rematches (never pair teams who already played)
    5. Handle byes (if odd number, lowest-ranked participant gets bye)
    """
    
    @staticmethod
    @transaction.atomic
    def generate_round(tournament_id: int, round_number: int):
        tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        
        # Get current standings
        standings = SwissStandingsService.get_standings(tournament_id)
        
        # Group by record
        record_groups = defaultdict(list)
        for participant in standings:
            record = f"{participant['wins']}-{participant['losses']}"
            record_groups[record].append(participant)
        
        pairings = []
        unpaired = []
        
        # Pair within each record group
        for record, participants in sorted(
            record_groups.items(),
            key=lambda x: -int(x[0].split('-')[0])  # Sort by wins descending
        ):
            # Sort by tiebreakers
            participants.sort(
                key=lambda p: (-p['buchholz_score'], -p['total_points']),
                reverse=False
            )
            
            while len(participants) >= 2:
                p1 = participants.pop(0)
                
                # Find opponent (first who hasn't played p1)
                opponent_found = False
                for i, p2 in enumerate(participants):
                    if not has_played_before(tournament_id, p1['id'], p2['id']):
                        opponent = participants.pop(i)
                        pairings.append((p1, opponent))
                        opponent_found = True
                        break
                
                # If no valid opponent found, move to unpaired
                if not opponent_found:
                    unpaired.append(p1)
            
            # Odd participant in group
            if participants:
                unpaired.append(participants[0])
        
        # Pair remaining unpaired participants
        while len(unpaired) >= 2:
            p1 = unpaired.pop(0)
            p2 = unpaired.pop(0)
            pairings.append((p1, p2))
        
        # Handle bye (if still unpaired)
        if unpaired:
            bye_participant = unpaired[0]
            pairings.append((bye_participant, None))  # Bye
        
        # Create matches
        for pair in pairings:
            Match.objects.create(
                tournament=tournament,
                round_number=round_number,
                participant1_id=pair[0]['id'],
                participant2_id=pair[1]['id'] if pair[1] else None,  # None = Bye
                state=Match.SCHEDULED
            )
        
        return pairings


def has_played_before(tournament_id: int, p1_id: int, p2_id: int) -> bool:
    """Check if two participants have already played each other."""
    return Match.objects.filter(
        tournament_id=tournament_id,
        participant1_id__in=[p1_id, p2_id],
        participant2_id__in=[p1_id, p2_id]
    ).exists()
```

**Swiss Standings with Buchholz Tiebreaker**:

```python
class SwissStandingsService:
    @staticmethod
    def get_standings(tournament_id: int) -> List[Dict]:
        """
        Calculate Swiss standings with Buchholz tiebreaker.
        
        Buchholz Score: Sum of opponent's total points.
        Used to break ties (played stronger opponents = higher Buchholz).
        """
        tournament = Tournament.objects.get(id=tournament_id)
        matches = Match.objects.filter(
            tournament=tournament,
            state=Match.COMPLETED
        )
        
        # Calculate points per participant
        participant_points = defaultdict(lambda: {
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'total_points': 0,
            'opponents': [],
        })
        
        for match in matches:
            p1_id = match.participant1_id
            p2_id = match.participant2_id
            
            # Calculate match points
            points = GameRulesEngine.calculate_match_points(
                game=tournament.game,
                result_data=match.result_data,
                tournament_format='SWISS'
            )
            
            participant_points[p1_id]['total_points'] += points['participant1_points']
            participant_points[p2_id]['total_points'] += points['participant2_points']
            
            # Track opponents
            participant_points[p1_id]['opponents'].append(p2_id)
            participant_points[p2_id]['opponents'].append(p1_id)
            
            # Track W/L
            if points['participant1_points'] > points['participant2_points']:
                participant_points[p1_id]['wins'] += 1
                participant_points[p2_id]['losses'] += 1
            elif points['participant2_points'] > points['participant1_points']:
                participant_points[p2_id]['wins'] += 1
                participant_points[p1_id]['losses'] += 1
            else:
                participant_points[p1_id]['draws'] += 1
                participant_points[p2_id]['draws'] += 1
        
        # Calculate Buchholz scores
        for p_id, data in participant_points.items():
            buchholz = sum(
                participant_points[opp_id]['total_points']
                for opp_id in data['opponents']
            )
            data['buchholz_score'] = buchholz
        
        # Sort standings
        sorted_standings = sorted(
            participant_points.items(),
            key=lambda x: (
                -x[1]['total_points'],   # Primary: Most points
                -x[1]['buchholz_score'], # Tiebreaker 1: Buchholz
                -x[1]['wins'],           # Tiebreaker 2: Most wins
            )
        )
        
        return [
            {
                'id': p_id,
                'rank': rank,
                **data
            }
            for rank, (p_id, data) in enumerate(sorted_standings, start=1)
        ]
```

---

#### 1.6.3 Multi-Map / Multi-Round Match Definitions

**Use Case**: Best-of-N series where each game is played on different map/mode (Valorant bo3: Ascent, Bind, Haven).

**Configuration**:

```python
class GameTournamentConfig(models.Model):
    # ... existing fields ...
    
    supports_best_of_series = models.BooleanField(default=False)
    best_of_options = models.JSONField(
        default=list,
        help_text='[1, 3, 5, 7] - Available best-of options'
    )
    map_pool = models.JSONField(
        default=list,
        help_text='["Ascent", "Bind", "Haven", "Split"] - Available maps'
    )
    map_selection_method = models.CharField(
        max_length=50,
        choices=[
            ('RANDOM', 'Random from pool'),
            ('PICK_BAN', 'Teams pick/ban maps'),
            ('PREDETERMINED', 'Organizer sets maps'),
        ],
        default='RANDOM'
    )
```

**Best-of-N Series Model**:

```python
# tournaments/models.py
class MatchSeries(models.Model):
    """
    Represents a best-of-N series (e.g., best-of-3, best-of-5).
    Container for multiple individual games.
    """
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE)
    round_number = models.PositiveIntegerField()
    
    participant1 = models.ForeignKey(
        'Team',
        related_name='series_as_p1',
        on_delete=models.CASCADE
    )
    participant2 = models.ForeignKey(
        'Team',
        related_name='series_as_p2',
        on_delete=models.CASCADE
    )
    
    # Series Configuration
    format = models.CharField(
        max_length=10,
        choices=[
            ('bo1', 'Best of 1'),
            ('bo3', 'Best of 3'),
            ('bo5', 'Best of 5'),
            ('bo7', 'Best of 7'),
        ]
    )
    games_to_win = models.PositiveIntegerField()  # 1, 2, 3, 4
    
    # Series State
    state = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='scheduled'
    )
    
    # Series Scores (games won)
    p1_games_won = models.PositiveIntegerField(default=0)
    p2_games_won = models.PositiveIntegerField(default=0)
    
    winner = models.ForeignKey(
        'Team',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='series_won'
    )
    
    scheduled_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class Game(models.Model):
    """
    Individual game within a best-of-N series.
    Each game is played on a specific map.
    """
    series = models.ForeignKey('MatchSeries', on_delete=models.CASCADE, related_name='games')
    game_number = models.PositiveIntegerField()  # 1, 2, 3, etc.
    
    # Map Selection
    map_name = models.CharField(max_length=100, blank=True)
    map_selected_by = models.CharField(
        max_length=20,
        choices=[
            ('p1', 'Participant 1'),
            ('p2', 'Participant 2'),
            ('random', 'Random'),
            ('organizer', 'Organizer'),
        ],
        blank=True
    )
    
    # Game Result
    winner = models.ForeignKey(
        'Team',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    result_data = models.JSONField(
        null=True,
        blank=True,
        help_text='{"team1_rounds": 13, "team2_rounds": 7}'
    )
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='scheduled'
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['game_number']
        unique_together = [('series', 'game_number')]
```

**Series Progression Logic**:

```python
# tournament_ops/services/series_service.py
class SeriesService:
    @staticmethod
    @transaction.atomic
    def submit_game_result(
        game_id: int,
        winner_id: int,
        result_data: Dict[str, Any]
    ) -> MatchSeries:
        """
        Submit result for one game in series.
        Automatically progress series and determine if series is complete.
        """
        game = Game.objects.select_related('series').get(id=game_id)
        series = game.series
        
        # Update game
        game.winner_id = winner_id
        game.result_data = result_data
        game.state = 'completed'
        game.completed_at = timezone.now()
        game.save()
        
        # Update series scores
        if winner_id == series.participant1_id:
            series.p1_games_won += 1
        else:
            series.p2_games_won += 1
        
        # Check if series is complete
        if series.p1_games_won >= series.games_to_win:
            series.winner_id = series.participant1_id
            series.state = 'completed'
            series.completed_at = timezone.now()
        elif series.p2_games_won >= series.games_to_win:
            series.winner_id = series.participant2_id
            series.state = 'completed'
            series.completed_at = timezone.now()
        else:
            # Series continues
            series.state = 'in_progress'
        
        series.save()
        
        # If series complete, publish event
        if series.state == 'completed':
            EventBus.publish(SeriesCompletedEvent(
                series_id=series.id,
                tournament_id=series.tournament_id,
                winner_id=series.winner_id
            ))
        
        return series
```

**Series Result Submission UI**:

```python
# Example JSON for multi-game result submission
{
    "series_id": 123,
    "games": [
        {
            "game_number": 1,
            "map_name": "Ascent",
            "winner_id": 456,  # Team A
            "team1_rounds": 13,
            "team2_rounds": 7
        },
        {
            "game_number": 2,
            "map_name": "Bind",
            "winner_id": 789,  # Team B
            "team1_rounds": 10,
            "team2_rounds": 13
        },
        {
            "game_number": 3,
            "map_name": "Haven",
            "winner_id": 456,  # Team A wins series 2-1
            "team1_rounds": 13,
            "team2_rounds": 11
        }
    ]
}
```

---

#### 1.6.4 Kill Points + Placement Points (PUBG System)

**Use Case**: Battle Royale games where scoring = Placement (1st-16th) + Kill Count.

**Configuration**:

```python
# PUBG Mobile Scoring Configuration
GameScoringRule.objects.create(
    game=pubg_mobile,
    tournament_format='SWISS',
    points_for_win=0,  # No binary win/loss
    points_for_loss=0,
    points_for_draw=0,
    bonus_rules={
        'placement_points': {
            1: 15,   # 1st place: 15 points
            2: 12,
            3: 10,
            4: 8,
            5: 6,
            6: 4,
            7: 2,
            8: 1,
            # 9-16: 0 points
        },
        'kill_points': 1,  # 1 point per kill
        'max_kills': 30,   # Cap at 30 kills
    },
    tiebreaker_order=[
        'total_points',
        'total_kills',
        'best_placement',
        'average_placement',
    ]
)
```

**PUBG Scoring Logic**:

```python
# games/rules/pubg_mobile_rules.py
class PUBGMobileGameRules:
    """Custom rules module for PUBG Mobile."""
    
    def __init__(self, game: Game):
        self.game = game
        self.scoring_rule = GameScoringRule.objects.get(
            game=game,
            tournament_format='SWISS'
        )
    
    def calculate_match_points(
        self,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """
        Calculate PUBG points: Placement + Kills.
        
        result_data = {
            'placement': 3,    # 3rd place
            'kills': 12,       # 12 kills
            'survival_time': 1800  # 30 minutes (optional)
        }
        
        Returns:
            {'participant1_points': Decimal('22')}  # 10 (placement) + 12 (kills)
        """
        placement = result_data.get('placement', 16)
        kills = result_data.get('kills', 0)
        
        # Get placement points from config
        placement_points_table = self.scoring_rule.bonus_rules['placement_points']
        placement_points = placement_points_table.get(str(placement), 0)
        
        # Get kill points
        kill_points_multiplier = self.scoring_rule.bonus_rules['kill_points']
        max_kills = self.scoring_rule.bonus_rules.get('max_kills', 999)
        kill_points = min(kills, max_kills) * kill_points_multiplier
        
        total_points = Decimal(str(placement_points + kill_points))
        
        return {
            'participant1_points': total_points,
            'participant2_points': Decimal('0'),  # PUBG is solo/squad, not 1v1
        }
    
    def validate_match_result(
        self,
        result_data: Dict[str, Any],
        tournament_config: 'GameTournamentConfig'
    ) -> tuple[bool, list[str]]:
        """
        Validate PUBG match result.
        
        Rules:
        - Placement: 1-16 (or 1-100 for large lobbies)
        - Kills: 0-max_kills (usually 0-30)
        - Survival time: optional, positive integer
        """
        errors = []
        
        # Validate placement
        placement = result_data.get('placement')
        if not placement:
            errors.append('Placement is required')
        elif not (1 <= placement <= 100):
            errors.append('Placement must be between 1 and 100')
        
        # Validate kills
        kills = result_data.get('kills')
        if kills is None:
            errors.append('Kill count is required')
        elif kills < 0:
            errors.append('Kills cannot be negative')
        elif kills > 30:
            errors.append('Kills cannot exceed 30 (suspicious)')
        
        # Validate survival time (optional)
        survival_time = result_data.get('survival_time')
        if survival_time is not None and survival_time < 0:
            errors.append('Survival time cannot be negative')
        
        return (len(errors) == 0, errors)
    
    def determine_winner(self, result_data: Dict[str, Any]) -> int:
        """
        PUBG doesn't have 1v1 winners.
        Return 1 to indicate result recorded.
        """
        return 1  # Single participant
```

**PUBG Match Result Submission**:

```json
{
    "match_id": 123,
    "result_data": {
        "placement": 3,
        "kills": 12,
        "survival_time": 1800,
        "squad_members": [
            {"player": "Player1", "kills": 5},
            {"player": "Player2", "kills": 4},
            {"player": "Player3", "kills": 2},
            {"player": "Player4", "kills": 1}
        ]
    },
    "proof_screenshot": "https://s3.../match_123_result.png"
}
```

---

#### 1.6.5 Time-Based Scoring (MOBA Speedrun Formats)

**Use Case**: MOBA tournaments where fastest clear time wins (e.g., fastest to destroy enemy Nexus in League of Legends).

**Configuration**:

```python
# League of Legends Speedrun Scoring
GameScoringRule.objects.create(
    game=league_of_legends,
    tournament_format='TIME_TRIAL',
    points_for_win=0,  # No binary win/loss
    points_for_loss=0,
    points_for_draw=0,
    bonus_rules={
        'scoring_type': 'time_based',
        'lower_is_better': True,  # Faster time = better
        'time_unit': 'seconds',
        'max_time': 3600,  # 1 hour max
        'objectives_bonus': {
            'first_blood': -30,     # -30 seconds bonus
            'first_tower': -60,
            'first_baron': -120,
        }
    },
    tiebreaker_order=[
        'fastest_time',
        'fewest_deaths',
        'most_objectives',
    ]
)
```

**Time-Based Scoring Logic**:

```python
class LOLSpeedrunGameRules:
    def calculate_match_points(
        self,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """
        Calculate LoL speedrun points based on clear time.
        
        result_data = {
            'clear_time_seconds': 1650,  # 27m 30s
            'objectives': {
                'first_blood': True,
                'first_tower': True,
                'first_baron': False,
            },
            'deaths': 3
        }
        """
        clear_time = result_data.get('clear_time_seconds', 3600)
        
        # Apply objective bonuses
        objectives = result_data.get('objectives', {})
        bonus_seconds = 0
        
        for objective, bonus in self.scoring_rule.bonus_rules['objectives_bonus'].items():
            if objectives.get(objective, False):
                bonus_seconds += bonus
        
        # Final time (lower is better)
        final_time = max(0, clear_time + bonus_seconds)
        
        # Convert to points (inverse of time for ranking)
        # Max points (3600) - time taken = higher points for faster clear
        max_time = self.scoring_rule.bonus_rules['max_time']
        points = Decimal(str(max_time - final_time))
        
        return {
            'participant1_points': points,
            'participant2_points': Decimal('0'),
        }
```

---

#### 1.6.6 Match Schema Concept

**Purpose**: Define expected input/output structure for each game format to enable frontend validation and backend enforcement.

**Match Schema Model**:

```python
class GameMatchSchema(models.Model):
    """
    JSON Schema defining expected structure for match input/result data.
    Enables frontend to dynamically generate forms and backend to validate.
    """
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='match_schemas')
    tournament_format = models.CharField(max_length=50)
    
    # Input Schema (what organizer/participants provide when creating/scheduling match)
    input_schema = models.JSONField(
        help_text='JSON Schema for match creation inputs (map, mode, time, etc.)'
    )
    
    # Result Schema (what participants submit after match completes)
    result_schema = models.JSONField(
        help_text='JSON Schema for match result submission (scores, winner, proof, etc.)'
    )
    
    # UI Hints (how frontend should render forms)
    ui_schema = models.JSONField(
        default=dict,
        help_text='UI hints for frontend: field order, widgets, help text'
    )
    
    class Meta:
        unique_together = [('game', 'tournament_format')]
```

**Example: Valorant Match Schema**:

```python
GameMatchSchema.objects.create(
    game=valorant,
    tournament_format='SINGLE_ELIMINATION',
    
    # Input Schema (match creation)
    input_schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "map_name": {
                "type": "string",
                "enum": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Breeze", "Fracture"],
                "description": "Map to be played"
            },
            "match_mode": {
                "type": "string",
                "enum": ["standard", "overtime"],
                "default": "standard"
            },
            "scheduled_time": {
                "type": "string",
                "format": "date-time",
                "description": "When match should start"
            },
            "server_region": {
                "type": "string",
                "enum": ["NA", "EU", "APAC", "LATAM", "BR"],
                "description": "Server region"
            }
        },
        "required": ["map_name", "scheduled_time", "server_region"]
    },
    
    # Result Schema (result submission)
    result_schema={
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "winner_id": {
                "type": "integer",
                "description": "ID of winning team"
            },
            "team1_rounds": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "Rounds won by Team 1"
            },
            "team2_rounds": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "Rounds won by Team 2"
            },
            "map_played": {
                "type": "string",
                "description": "Map that was played"
            },
            "match_duration_minutes": {
                "type": "integer",
                "minimum": 0,
                "description": "How long match lasted"
            },
            "overtime_played": {
                "type": "boolean",
                "description": "Whether overtime was needed"
            },
            "proof_screenshot_url": {
                "type": "string",
                "format": "uri",
                "description": "Screenshot of final scoreboard"
            }
        },
        "required": ["winner_id", "team1_rounds", "team2_rounds", "proof_screenshot_url"]
    },
    
    # UI Schema (frontend rendering hints)
    ui_schema={
        "ui:order": ["map_name", "team1_rounds", "team2_rounds", "winner_id", "proof_screenshot_url"],
        "map_name": {
            "ui:widget": "select",
            "ui:help": "Select the map played in this match"
        },
        "team1_rounds": {
            "ui:widget": "number",
            "ui:help": "Number of rounds won by Team 1 (0-25)"
        },
        "team2_rounds": {
            "ui:widget": "number",
            "ui:help": "Number of rounds won by Team 2 (0-25)"
        },
        "winner_id": {
            "ui:widget": "radio",
            "ui:help": "Select the winning team"
        },
        "proof_screenshot_url": {
            "ui:widget": "file",
            "ui:accept": "image/*",
            "ui:help": "Upload screenshot of final scoreboard showing all players and scores"
        }
    }
)
```

**Schema Validation Service**:

```python
# games/services/schema_validation_service.py
import jsonschema
from jsonschema import validate, ValidationError

class SchemaValidationService:
    @staticmethod
    def validate_match_result(
        game: Game,
        tournament_format: str,
        result_data: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate match result against game's result schema.
        
        Returns:
            (is_valid, error_messages)
        """
        try:
            schema = GameMatchSchema.objects.get(
                game=game,
                tournament_format=tournament_format
            )
        except GameMatchSchema.DoesNotExist:
            # No schema defined, skip validation
            return (True, [])
        
        try:
            validate(instance=result_data, schema=schema.result_schema)
            return (True, [])
        except ValidationError as e:
            # Parse JSON Schema error messages
            errors = [e.message]
            if e.context:
                errors.extend([err.message for err in e.context])
            return (False, errors)
    
    @staticmethod
    def validate_match_input(
        game: Game,
        tournament_format: str,
        input_data: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate match creation inputs against game's input schema."""
        try:
            schema = GameMatchSchema.objects.get(
                game=game,
                tournament_format=tournament_format
            )
        except GameMatchSchema.DoesNotExist:
            return (True, [])
        
        try:
            validate(instance=input_data, schema=schema.input_schema)
            return (True, [])
        except ValidationError as e:
            errors = [e.message]
            if e.context:
                errors.extend([err.message for err in e.context])
            return (False, errors)
```

---

### 1.7 Benefits of Expanded Game Rules Layer

**Flexibility**:
- ✅ Support complex scoring (placement + kills, time-based, group stage)
- ✅ Support multi-stage tournaments (Swiss → Top 8, Groups → Knockout)
- ✅ Support best-of-N series with map selection
- ✅ Add new games via admin (no code deployment)
- ✅ Custom rules modules for complex games (Valorant overtime, PUBG scoring)
- ✅ Fallback to config-driven defaults for simple games

**Maintainability**:
- ✅ No hardcoded if-else chains (7 game checks → 0)
- ✅ Clear separation: Config vs. Custom Logic
- ✅ Game-agnostic tournament system
- ✅ JSON Schema validation (frontend + backend use same schema)

**Extensibility**:
- ✅ Easy to add new tournament formats (Swiss, League, Time Trial)
- ✅ Easy to add new scoring systems (K/D ratio, objectives, speedrun)
- ✅ Easy to add game-specific validation (rank checks, region locks)
- ✅ Frontend can dynamically generate forms from schemas

---

## 2. Result Input Pipeline (No Game APIs)

### 2.1 Problem Statement

**Reality**: DeltaCrown operates in a **no direct game API integration** environment. Unlike platforms with official API access (Riot Games API for Valorant, Steam API for CS2), DeltaCrown cannot automatically fetch match results.

**Challenge**: How to ensure result accuracy and prevent fraud without automated verification?

**Solution**: **Manual submission → Verification → Finalization pipeline** with multiple checkpoints.

---

### 2.2 Result Pipeline Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    RESULT INPUT PIPELINE                         │
│              (No Game API - Manual Verification)                 │
└──────────────────────────────────────────────────────────────────┘

STEP 1: Player Submits Result
├─> User/Team navigates to match page
├─> Clicks "Submit Result"
├─> Fills form:
│   • Select winner (Team A / Team B)
│   • Enter scores (13-7, 3-1, etc.)
│   • Upload proof screenshot (required)
│   • Add notes (optional)
├─> Validation:
│   • Winner must match scores (Team A score > Team B score)
│   • Scores must be valid for game (Valorant: 0-25, PUBG: 1-100 placement)
│   • Screenshot required (enforced)
└─> CREATE: MatchResultSubmission record (status: PENDING)

        │
        ▼

STEP 2: Opponent Notified
├─> Opponent receives notification:
│   "Team A submitted match result. Please confirm or dispute."
├─> Opponent views submission:
│   • Claimed winner
│   • Scores
│   • Proof screenshot
│   • Submitted by (username)
│   • Submitted at (timestamp)
└─> Opponent has 3 options:
    ├─> CONFIRM → Go to Step 3a
    ├─> DISPUTE → Go to Step 3b
    └─> IGNORE → Auto-confirm after 24 hours → Go to Step 3a

        │
        ▼

STEP 3a: Opponent Confirms
├─> MatchResultSubmission.status = CONFIRMED
├─> If organizer review disabled:
│   └─> Go directly to Step 5 (Finalize)
└─> If organizer review enabled:
    └─> Go to Step 4 (Organizer Review)

STEP 3b: Opponent Disputes
├─> Opponent clicks "Dispute Result"
├─> Fills dispute form:
│   • Reason (dropdown: Incorrect score, Fake proof, Cheating, etc.)
│   • Explanation (text, min 50 chars)
│   • Counter-proof screenshot (optional)
├─> CREATE: DisputeRecord (status: PENDING)
├─> MatchResultSubmission.status = DISPUTED
├─> Match.state = DISPUTED
└─> Organizer receives notification:
    "Match #123 has a disputed result. Review required."
    └─> Go to Step 4 (Organizer Review)

        │
        ▼

STEP 4: Organizer Reviews in Results Inbox
├─> Organizer navigates to Results Inbox
├─> Sees pending/disputed results queue:
│   • Pending results (awaiting confirmation)
│   • Conflicted results (both teams submitted different winners)
│   • Disputed results (opponent disputed original submission)
├─> Organizer clicks "Review" on submission
├─> Views submission details:
│   • Original submission (claimed winner, scores, proof)
│   • Dispute (if any): reason, explanation, counter-proof
│   • Match details (tournament, round, participants)
├─> Organizer makes decision:
│   ├─> APPROVE ORIGINAL → Finalize with original submission
│   ├─> APPROVE DISPUTE → Override result with dispute claim
│   ├─> ORDER REMATCH → Reset match, teams must replay
│   └─> REQUEST MORE INFO → Ask for additional proof/clarification
└─> Organizer enters resolution notes (why this decision)
    └─> Go to Step 5 (Finalize)

        │
        ▼

STEP 5: TournamentOps Validates & Finalizes
├─> TournamentOps.ResultVerificationService.finalize_result()
├─> Validate result against game rules:
│   • Schema validation (result matches game's expected structure)
│   • Business logic validation (scores valid for format, winner correct)
│   • Game-specific validation (Valorant rounds 0-25, PUBG placement 1-100)
├─> If invalid:
│   └─> Reject submission, notify organizer + participants
├─> If valid:
│   ├─> Apply result to Match:
│   │   • Match.winner = winner_id
│   │   • Match.result_data = {scores, map, etc.}
│   │   • Match.state = COMPLETED
│   ├─> Mark submission as APPROVED
│   ├─> Reject conflicting submissions (if any)
│   └─> Publish MatchCompletedEvent
└─> Go to Step 6 (Event Propagation)

        │
        ▼

STEP 6: Event-Driven Updates
├─> MatchCompletedEvent published to EventBus
├─> Event Handlers triggered:
│   ├─> BracketService.advance_winner()
│   │   └─> Winner added to next round match
│   ├─> TeamStatsService.record_match_result()
│   │   ├─> Team.matches_played += 1
│   │   ├─> Team.matches_won += 1 (winner)
│   │   └─> Team.win_rate recalculated
│   ├─> UserStatsService.record_match_result()
│   │   ├─> User.matches_played += 1 (all players)
│   │   ├─> User.matches_won += 1 (winning team players)
│   │   └─> User.win_rate recalculated
│   ├─> MatchHistoryService.create_history_entry()
│   │   └─> TeamMatchHistory record created
│   ├─> RankingService.update_elo_ratings()
│   │   ├─> Winner ELO += 25
│   │   └─> Loser ELO -= 25
│   ├─> LeaderboardService.update_standings()
│   │   └─> Tournament points awarded (if applicable)
│   ├─> PayoutService.award_match_bonus()
│   │   └─> Winner receives DeltaCoin bonus (if configured)
│   └─> NotificationService.send_result_notifications()
│       ├─> Winner: "You won! Advancing to Round 2."
│       └─> Loser: "Match complete. Better luck next time."
└─> Pipeline Complete ✅
```

---

### 2.3 Data Models for Result Pipeline

#### Model 1: MatchResultSubmission

```python
# tournaments/models.py
class MatchResultSubmission(models.Model):
    """
    Queue for pending match result submissions.
    Enables multi-step verification workflow.
    """
    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='result_submissions')
    
    # Submitter
    submitted_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    submitted_by_team = models.ForeignKey(
        'teams.Team',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Which team this submitter represents'
    )
    
    # Result Data
    claimed_winner_id = models.IntegerField(
        help_text='ID of claimed winning participant (Team or User)'
    )
    result_data = models.JSONField(
        help_text='Match result: {"team1_rounds": 13, "team2_rounds": 7, "map": "Ascent"}'
    )
    
    # Proof
    proof_screenshot = models.ImageField(
        upload_to='match_results/',
        help_text='Screenshot of final scoreboard'
    )
    proof_url = models.URLField(
        blank=True,
        help_text='Alternative: external proof URL (YouTube clip, Twitch VOD)'
    )
    notes = models.TextField(
        blank=True,
        help_text='Additional notes from submitter'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Opponent Confirmation'),
            ('confirmed', 'Confirmed by Opponent'),
            ('disputed', 'Disputed by Opponent'),
            ('approved', 'Approved by Organizer'),
            ('rejected', 'Rejected by Organizer'),
        ],
        default='pending'
    )
    
    # Review
    reviewed_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_submissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        blank=True,
        help_text='Organizer notes on approval/rejection'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
```

#### Model 2: DisputeRecord (Enhanced)

```python
# tournaments/models.py
class DisputeRecord(models.Model):
    """
    Dispute submitted by opponent against result submission.
    """
    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='disputes')
    original_submission = models.ForeignKey(
        'MatchResultSubmission',
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    
    # Disputer
    disputed_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    disputed_by_team = models.ForeignKey(
        'teams.Team',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    
    # Dispute Details
    reason = models.CharField(
        max_length=50,
        choices=[
            ('incorrect_score', 'Incorrect Score'),
            ('fake_proof', 'Fake/Manipulated Proof'),
            ('cheating', 'Opponent Cheated'),
            ('wrong_winner', 'Wrong Winner'),
            ('no_show', 'Opponent No-Show (forfeit claim is wrong)'),
            ('other', 'Other'),
        ]
    )
    explanation = models.TextField(
        help_text='Detailed explanation (min 50 characters)'
    )
    
    # Counter-Claim
    claimed_correct_winner_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='What disputer claims is the correct winner'
    )
    claimed_correct_scores = models.JSONField(
        null=True,
        blank=True,
        help_text='What disputer claims are the correct scores'
    )
    counter_proof_screenshot = models.ImageField(
        upload_to='disputes/',
        null=True,
        blank=True,
        help_text='Counter-proof screenshot'
    )
    counter_proof_url = models.URLField(
        blank=True,
        help_text='Counter-proof external URL'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Organizer Review'),
            ('resolved', 'Resolved'),
            ('escalated', 'Escalated to Admin'),
        ],
        default='pending'
    )
    
    # Resolution
    resolved_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_disputes'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.CharField(
        max_length=50,
        choices=[
            ('approve_original', 'Original Submission Approved'),
            ('approve_dispute', 'Dispute Upheld'),
            ('rematch', 'Order Rematch'),
            ('no_action', 'No Action Taken'),
        ],
        blank=True
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text='Organizer explanation of decision'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]
```

---

### 2.4 TournamentOps Services for Result Pipeline

#### Service 1: ResultSubmissionService

```python
# tournament_ops/services/result_submission_service.py
class ResultSubmissionService:
    """Handle initial result submission by participants."""
    
    @staticmethod
    @transaction.atomic
    def submit_result(
        match_id: int,
        submitter_user_id: int,
        claimed_winner_id: int,
        result_data: Dict[str, Any],
        proof_screenshot: 'UploadedFile',
        notes: str = ''
    ) -> MatchResultSubmission:
        """
        Submit match result (Step 1 of pipeline).
        
        Workflow:
        1. Validate match is in correct state (LIVE or COMPLETED)
        2. Validate submitter is participant in match
        3. Validate result data against game schema
        4. Create MatchResultSubmission record
        5. Notify opponent
        """
        match = Match.objects.select_related('tournament__game').get(id=match_id)
        submitter = User.objects.get(id=submitter_user_id)
        
        # Validate match state
        if match.state not in [Match.LIVE, Match.COMPLETED]:
            raise ValidationError('Match must be LIVE or COMPLETED to submit results')
        
        # Validate submitter is participant
        if not match.is_participant(submitter):
            raise PermissionDenied('You are not a participant in this match')
        
        # Validate result data against game schema
        is_valid, errors = SchemaValidationService.validate_match_result(
            game=match.tournament.game,
            tournament_format=match.tournament.format,
            result_data=result_data
        )
        if not is_valid:
            raise ValidationError(errors)
        
        # Create submission
        submission = MatchResultSubmission.objects.create(
            match=match,
            submitted_by=submitter,
            submitted_by_team=match.get_participant_team(submitter),
            claimed_winner_id=claimed_winner_id,
            result_data=result_data,
            proof_screenshot=proof_screenshot,
            notes=notes,
            status='pending'
        )
        
        # Update match state
        match.state = Match.PENDING_RESULT
        match.save()
        
        # Notify opponent
        opponent = match.get_opponent(submitter)
        NotificationService.send_result_submitted_notification(
            recipient=opponent,
            match=match,
            submission=submission
        )
        
        return submission
```

#### Service 2: ResultVerificationService

```python
# tournament_ops/services/result_verification_service.py
class ResultVerificationService:
    """
    Orchestrate result verification and finalization (Step 5 of pipeline).
    Core TournamentOps service that validates and finalizes results.
    """
    
    @staticmethod
    @transaction.atomic
    def finalize_result(
        submission_id: int,
        approved_by_user_id: int = None,
        approval_notes: str = ''
    ) -> Match:
        """
        Finalize result after validation.
        
        Workflow:
        1. Get submission
        2. Validate result (schema + game rules)
        3. Apply result to Match
        4. Mark submission as approved
        5. Reject conflicting submissions
        6. Publish MatchCompletedEvent
        7. Advance winner to next round
        8. Send notifications
        """
        submission = MatchResultSubmission.objects.select_related(
            'match__tournament__game'
        ).get(id=submission_id)
        match = submission.match
        game = match.tournament.game
        
        # Validate result (schema + rules)
        is_valid, errors = GameRulesEngine.get_rules(game).validate_match_result(
            result_data=submission.result_data,
            tournament_config=match.tournament.config
        )
        if not is_valid:
            # Reject submission
            submission.status = 'rejected'
            submission.reviewed_by_id = approved_by_user_id
            submission.reviewed_at = timezone.now()
            submission.review_notes = f"Validation failed: {', '.join(errors)}"
            submission.save()
            
            raise ValidationError(errors)
        
        # Apply result to Match
        match.result_data = submission.result_data
        match.winner_id = submission.claimed_winner_id
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()
        
        # Mark submission approved
        submission.status = 'approved'
        submission.reviewed_by_id = approved_by_user_id
        submission.reviewed_at = timezone.now()
        submission.review_notes = approval_notes
        submission.save()
        
        # Reject conflicting submissions
        MatchResultSubmission.objects.filter(
            match=match,
            status__in=['pending', 'disputed']
        ).exclude(id=submission.id).update(
            status='rejected',
            reviewed_by_id=approved_by_user_id,
            reviewed_at=timezone.now(),
            review_notes='Conflicting submission rejected'
        )
        
        # Publish event (triggers Step 6: Event Propagation)
        EventBus.publish(MatchCompletedEvent(
            match_id=match.id,
            tournament_id=match.tournament_id,
            winner_id=match.winner_id,
            loser_id=match.get_loser_id(),
            result_data=match.result_data
        ))
        
        # Advance winner to next round
        if match.next_match_id:
            BracketService.advance_winner(match_id=match.id)
        
        # Notify participants
        NotificationService.send_result_finalized_notification(
            match=match,
            submission=submission
        )
        
        return match
```

---

### 2.5 Benefits of Result Input Pipeline

**Integrity**:
- ✅ Multi-step verification (submit → opponent confirm → organizer review)
- ✅ Proof required (screenshot upload mandatory)
- ✅ Schema validation (JSON Schema + game rules validation)
- ✅ Dispute mechanism (opponent can challenge results)

**Transparency**:
- ✅ All submissions logged (audit trail)
- ✅ Disputes tracked with reasons (clear record of conflicts)
- ✅ Organizer decisions logged (resolution notes)

**Automation**:
- ✅ Event-driven updates (stats, rankings, leaderboards auto-update)
- ✅ Auto-confirmation after 24 hours (prevent blocking)
- ✅ Auto-advancement (winner progresses to next round)

**Flexibility**:
- ✅ Configurable organizer review (required vs. optional)
- ✅ Multiple resolution options (approve, reject, rematch)
- ✅ Works for all game types (via schema validation)

---

## 3. Smart Registration (Expanded)

### 3.1 Design Principles

**Core Goals**:
1. **Auto-Fill Intelligence**: Pre-populate from UserProfile, Team, Game configs
2. **Field Locking**: Lock verified fields (email, game IDs) to prevent fraud
3. **Unique Tracking**: Assign registration number for support/certificates
4. **Game-Agnostic**: Works for all 11 games via configuration
5. **Solo & Team Support**: Single workflow for both types
6. **Draft Persistence**: Resume registration across devices/sessions
7. **Game-Aware Questions**: Dynamic form fields based on game format
8. **Conditional Inputs**: Show/hide fields based on user selections
9. **Document Requirements**: Support for required screenshots/documents
10. **Organizer Verification**: Admin checklist for registration approval

---

### 3.2 Registration Data Model

```python
class RegistrationDraft(models.Model):
    """
    Persistent draft storage for multi-session registration.
    Allows cross-device resume, auto-save, progress tracking.
    """
    # Identity
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Human-readable: VCT-2025-001234'
    )
    
    # Relationships
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE)
    team = models.ForeignKey('teams.Team', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Draft Data
    form_data = models.JSONField(
        default=dict,
        help_text='All form fields: {riot_id, discord, phone, ...}'
    )
    auto_filled_fields = models.JSONField(
        default=list,
        help_text='List of fields auto-filled: ["riot_id", "email"]'
    )
    locked_fields = models.JSONField(
        default=list,
        help_text='List of fields locked: ["email", "riot_id"]'
    )
    
    # Progress
    current_step = models.CharField(
        max_length=20,
        default='player_info',
        choices=[
            ('player_info', 'Player Information'),
            ('team_info', 'Team Information'),
            ('review', 'Review & Confirm'),
            ('payment', 'Payment'),
        ]
    )
    completion_percentage = models.PositiveIntegerField(default=0)
    
    # Status
    submitted = models.BooleanField(default=False)
    registration = models.OneToOneField(
        'Registration',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Created after submission'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_saved_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        help_text='Draft expires 7 days after creation'
    )
    
    class Meta:
        unique_together = [('user', 'tournament')]
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['registration_number']),
        ]
```

**Registration Number Format**:
```python
# Format: {GAME_PREFIX}-{YEAR}-{SEQUENCE}
# Examples:
#   VCT-2025-001234  (Valorant Champions Tour)
#   PUBG-2025-005678 (PUBG Mobile)
#   CS2-2025-000123  (Counter-Strike 2)

def generate_registration_number(tournament: Tournament) -> str:
    game_prefix = tournament.game.slug.upper()[:4]
    year = timezone.now().year
    
    # Get next sequence for this game+year
    last_reg = RegistrationDraft.objects.filter(
        tournament__game=tournament.game,
        registration_number__startswith=f'{game_prefix}-{year}'
    ).order_by('-registration_number').first()
    
    if last_reg:
        last_seq = int(last_reg.registration_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    
    return f'{game_prefix}-{year}-{next_seq:06d}'
```

---

### 2.3 Auto-Fill System

#### Auto-Fill Data Structure

```python
@dataclass
class AutoFillField:
    """
    Represents an auto-filled field with metadata.
    """
    value: Any
    source: str  # 'profile' | 'team' | 'game_account' | 'manual'
    confidence: str  # 'high' | 'medium' | 'low'
    locked: bool = False  # If True, field cannot be edited
    verified: bool = False  # If True, value has been verified (OAuth, email, etc.)
    help_text: str = ''
    validation_pattern: str = None
```

---

#### Auto-Fill Service

```python
# tournaments/services/registration_autofill_service.py
class RegistrationAutoFillService:
    """
    Intelligent auto-fill service using game configs.
    Replaces hardcoded game checks.
    """
    
    @staticmethod
    def generate_autofill_data(
        user: User,
        tournament: Tournament,
        team: Team = None
    ) -> Dict[str, AutoFillField]:
        """
        Generate auto-fill data for registration form.
        Uses GamePlayerIdentityConfig to know which fields to populate.
        """
        autofill_data = {}
        user_profile = user.profile
        game = tournament.game
        
        # 1. Auto-fill USER fields (always same)
        autofill_data['email'] = AutoFillField(
            value=user.email,
            source='profile',
            confidence='high',
            locked=user.email_verified,  # Lock if verified
            verified=user.email_verified,
            help_text='Your account email'
        )
        
        autofill_data['phone'] = AutoFillField(
            value=user_profile.phone or '',
            source='profile',
            confidence='high' if user_profile.phone else 'low',
            locked=user_profile.phone_verified,
            verified=user_profile.phone_verified,
            help_text='Your phone number'
        )
        
        autofill_data['discord'] = AutoFillField(
            value=user_profile.discord or '',
            source='profile',
            confidence='medium',
            locked=False,  # Discord can always be changed
            help_text='Your Discord username'
        )
        
        # 2. Auto-fill GAME-SPECIFIC fields (from config)
        identity_configs = GamePlayerIdentityConfig.objects.filter(
            game=game
        ).order_by('display_order')
        
        for config in identity_configs:
            field_value = getattr(user_profile, config.field_name, None)
            
            autofill_data[config.field_name] = AutoFillField(
                value=field_value or '',
                source='game_account',
                confidence='high' if field_value else 'low',
                locked=config.is_immutable and bool(field_value),  # Lock if immutable + has value
                verified=False,  # TODO: Check verification status
                help_text=config.help_text,
                validation_pattern=config.validation_pattern
            )
        
        # 3. Auto-fill TEAM fields (if team tournament)
        if tournament.is_team_based and team:
            autofill_data['team_name'] = AutoFillField(
                value=team.name,
                source='team',
                confidence='high',
                locked=team.is_verified,  # Lock verified team names
                help_text='Your team name'
            )
            
            autofill_data['team_captain'] = AutoFillField(
                value=team.captain.username,
                source='team',
                confidence='high',
                locked=True,  # Captain cannot be changed in registration
                help_text='Team captain'
            )
            
            # Team members (display only, not editable)
            members = [m.user.username for m in team.members.all()]
            autofill_data['team_members'] = AutoFillField(
                value=', '.join(members),
                source='team',
                confidence='high',
                locked=True,
                help_text='Team roster'
            )
        
        return autofill_data
```

---

### 2.4 Registration Workflow

#### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: ELIGIBILITY CHECK (Pre-Registration)               │
│  - Check tournament requirements (age, rank, region)       │
│  - Check user verification status (email, game account)    │
│  - Check team eligibility (size, game match)               │
│  - Display PASS/FAIL with specific reasons                 │
│  - Only show "Register" button if PASS                     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STEP 2: CREATE DRAFT (Server-Side)                         │
│  POST /api/tournaments/{slug}/registrations/drafts/         │
│  - Generate unique registration number                     │
│  - Create RegistrationDraft record                         │
│  - Generate auto-fill data (via AutoFillService)           │
│  - Return draft UUID + registration number                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STEP 3: MULTI-STEP FORM (With Auto-Save)                   │
│  Step 3a: Player Information                               │
│   - Render fields from GamePlayerIdentityConfig            │
│   - Lock verified fields (show lock icon)                  │
│   - Auto-save every 30 seconds (PUT /drafts/{uuid}/)       │
│                                                             │
│  Step 3b: Team Information (if team tournament)            │
│   - Show team data (name, captain, roster)                 │
│   - All fields locked (managed via Teams app)              │
│                                                             │
│  Step 3c: Additional Info                                  │
│   - Discord, phone, age confirmation                       │
│   - Terms & conditions acceptance                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STEP 4: REVIEW & SUBMIT                                     │
│  - Display all data (with edit links for unlocked fields)  │
│  - Show registration number: VCT-2025-001234               │
│  - Final eligibility check (server-side)                   │
│  - Submit button triggers:                                 │
│    POST /api/tournaments/{slug}/registrations/              │
│    (Atomic transaction: Create Registration + Payment)     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STEP 5: PAYMENT (If Required)                              │
│  - DeltaCoin: Instant deduction → CONFIRMED                │
│  - Manual: Upload proof → PENDING                          │
│  - Payment gateway: Redirect → Callback → CONFIRMED        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ STEP 6: CONFIRMATION                                        │
│  - Display registration number                             │
│  - Email confirmation (details + receipt + calendar)       │
│  - Add to "My Tournaments" dashboard                       │
│  - Show next steps (check-in time, bracket publish date)   │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.5 API Endpoints

#### REST API Design

```python
# Registration Drafts API
POST   /api/v1/tournaments/{slug}/registrations/drafts/
  Body: {}
  Response: {
    "uuid": "abc123-def456",
    "registration_number": "VCT-2025-001234",
    "resume_url": "/register/abc123-def456",
    "auto_fill_data": {...},
    "locked_fields": ["email", "riot_id"],
    "current_step": "player_info",
    "expires_at": "2025-12-15T00:00:00Z"
  }

GET    /api/v1/registrations/drafts/{uuid}/
  Response: {draft details, form_data, progress}

PUT    /api/v1/registrations/drafts/{uuid}/
  Body: {"form_data": {...}, "current_step": "team_info"}
  Response: {updated draft, validation_errors}

POST   /api/v1/registrations/drafts/{uuid}/submit/
  Body: {final form_data}
  Response: {
    "registration_id": 123,
    "payment_required": true,
    "payment_amount": "10.00",
    "payment_methods": ["deltacoin", "manual"]
  }

DELETE /api/v1/registrations/drafts/{uuid}/
  Response: 204 No Content

# Registration Management API
GET    /api/v1/registrations/{id}/
  Response: {registration details, status, payment}

POST   /api/v1/registrations/{id}/withdraw/
  Body: {"reason": "Can't attend"}
  Response: {registration marked WITHDRAWN, refund processed}

# Payment API
POST   /api/v1/registrations/{id}/payments/
  Body: {
    "method": "deltacoin" | "manual",
    "proof_image": "base64..." (if manual)
  }
  Response: {payment_id, status}

GET    /api/v1/payments/{id}/status/
  Response: {"status": "PENDING" | "VERIFIED" | "REJECTED"}

# Field Validation API (Real-Time)
POST   /api/v1/validate-field/
  Body: {
    "game_id": 1,
    "field_name": "riot_id",
    "value": "Player#1234"
  }
  Response: {
    "valid": true,
    "errors": [],
    "suggestions": []
  }
```

---

### 3.3 Game-Aware Registration Questions

**Dynamic Field Configuration**:

```python
# games/models.py
class GameRegistrationQuestionConfig(models.Model):
    """
    Per-game additional registration questions.
    Enables game-specific data collection.
    """
    game = models.ForeignKey('Game', on_delete=models.CASCADE, related_name='registration_questions')
    
    question_key = models.CharField(
        max_length=100,
        help_text='Internal field name: preferred_role, rank_tier, server_region'
    )
    question_text = models.CharField(
        max_length=255,
        help_text='Display text: "What is your preferred role?"'
    )
    field_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text Input'),
            ('select', 'Dropdown'),
            ('multi_select', 'Multi-Select'),
            ('radio', 'Radio Buttons'),
            ('number', 'Number'),
            ('file', 'File Upload'),
        ]
    )
    options = models.JSONField(
        default=list,
        help_text='For select/multi_select: ["Duelist", "Controller", "Sentinel", "Initiator"]'
    )
    is_required = models.BooleanField(default=False)
    help_text = models.TextField(blank=True)
    validation_rules = models.JSONField(
        default=dict,
        help_text='{"min_length": 3, "max_length": 50, "pattern": "^[A-Za-z]+$"}'
    )
    display_order = models.PositiveIntegerField(default=0)
    
    # Conditional Display
    show_if = models.JSONField(
        default=dict,
        blank=True,
        help_text='Condition for showing field: {"field": "tournament_type", "value": "ranked"}'
    )
    
    class Meta:
        ordering = ['display_order']
        unique_together = [('game', 'question_key')]
```

**Example: Valorant Registration Questions**:

```python
# Valorant-specific questions
GameRegistrationQuestionConfig.objects.bulk_create([
    GameRegistrationQuestionConfig(
        game=valorant,
        question_key='preferred_role',
        question_text='What is your preferred role?',
        field_type='select',
        options=['Duelist', 'Controller', 'Sentinel', 'Initiator', 'Flex'],
        is_required=True,
        help_text='Select your main role',
        display_order=1
    ),
    GameRegistrationQuestionConfig(
        game=valorant,
        question_key='rank_tier',
        question_text='Current Competitive Rank',
        field_type='select',
        options=['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Immortal', 'Radiant'],
        is_required=True,
        help_text='Your current rank this season',
        display_order=2
    ),
    GameRegistrationQuestionConfig(
        game=valorant,
        question_key='rank_screenshot',
        question_text='Upload Rank Screenshot',
        field_type='file',
        is_required=True,
        help_text='Upload screenshot of your in-game rank',
        validation_rules={'max_file_size_mb': 5, 'allowed_formats': ['jpg', 'png']},
        display_order=3
    ),
])
```

---

### 3.4 Conditional Inputs Based on Game Format

**Frontend Conditional Logic**:

```javascript
// Show/hide fields based on conditions
function shouldShowField(field, formData) {
    if (!field.show_if || Object.keys(field.show_if).length === 0) {
        return true;  // No conditions, always show
    }
    
    // Check all conditions
    for (const [conditionField, conditionValue] of Object.entries(field.show_if)) {
        if (formData[conditionField] !== conditionValue) {
            return false;  // Condition not met
        }
    }
    
    return true;  // All conditions met
}

// Usage in React component
const visibleFields = registrationQuestions.filter(field => 
    shouldShowField(field, formData)
);
```

**Example: Conditional Questions**:

```python
# Show "Team Role" only if tournament is team-based
GameRegistrationQuestionConfig.objects.create(
    game=valorant,
    question_key='team_role',
    question_text='Your Role in Team',
    field_type='select',
    options=['Captain', 'Co-Captain', 'Member'],
    is_required=True,
    show_if={'tournament_type': 'team'},  # Only show for team tournaments
    display_order=5
)
```

---

### 3.5 Required Documents/Screenshots

**Document Requirements Model**:

```python
# tournaments/models.py
class TournamentDocumentRequirement(models.Model):
    """
    Required documents for tournament registration.
    Examples: rank screenshot, ID verification, parent consent (for minors).
    """
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='document_requirements')
    
    document_type = models.CharField(
        max_length=50,
        choices=[
            ('rank_screenshot', 'Rank Screenshot'),
            ('id_verification', 'ID Verification'),
            ('parent_consent', 'Parent Consent Form (Minors)'),
            ('payment_proof', 'Payment Proof'),
            ('team_roster', 'Team Roster Screenshot'),
            ('custom', 'Custom Document'),
        ]
    )
    display_name = models.CharField(
        max_length=255,
        help_text='Displayed to user: "Upload your rank screenshot"'
    )
    description = models.TextField(
        help_text='Instructions: "Screenshot must show your in-game rank and username"'
    )
    is_required = models.BooleanField(default=True)
    max_file_size_mb = models.PositiveIntegerField(default=5)
    allowed_formats = models.JSONField(
        default=list,
        help_text='["jpg", "png", "pdf"]'
    )
    
    # Conditional requirement
    required_if = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"user_age": "<18"} - Require parent consent if under 18'
    )
    
    class Meta:
        ordering = ['document_type']


class RegistrationDocumentUpload(models.Model):
    """Stores uploaded documents for registration."""
    registration = models.ForeignKey('Registration', on_delete=models.CASCADE, related_name='documents')
    document_requirement = models.ForeignKey('TournamentDocumentRequirement', on_delete=models.CASCADE)
    
    file = models.FileField(upload_to='registration_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
```

---

### 3.6 Registration Draft Recovery

**Enhanced Draft Model with Recovery**:

```python
class RegistrationDraft(models.Model):
    # ... existing fields ...
    
    # Recovery Features
    recovery_email_sent = models.BooleanField(default=False)
    recovery_email_sent_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    
    # Browser fingerprinting (for cross-device detection)
    browser_fingerprint = models.CharField(
        max_length=255,
        blank=True,
        help_text='Browser fingerprint for recovery'
    )
    
    # Session tracking
    session_count = models.PositiveIntegerField(
        default=1,
        help_text='Number of times draft was accessed'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-last_activity_at']),
            models.Index(fields=['expires_at']),
        ]
```

**Draft Recovery Service**:

```python
# tournaments/services/draft_recovery_service.py
class DraftRecoveryService:
    """Handle draft recovery across devices/sessions."""
    
    @staticmethod
    def find_drafts_for_user(user_id: int) -> List[RegistrationDraft]:
        """Find all active drafts for user."""
        return RegistrationDraft.objects.filter(
            user_id=user_id,
            submitted=False,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity_at')
    
    @staticmethod
    def send_recovery_email(draft_id: int):
        """Send recovery email with link to resume draft."""
        draft = RegistrationDraft.objects.get(id=draft_id)
        
        if draft.recovery_email_sent:
            return  # Already sent
        
        resume_url = f"https://deltacrown.com/register/resume/{draft.uuid}"
        
        send_email(
            to=draft.user.email,
            subject=f"Resume your {draft.tournament.name} registration",
            template='registration_recovery.html',
            context={
                'user': draft.user,
                'tournament': draft.tournament,
                'registration_number': draft.registration_number,
                'completion_percentage': draft.completion_percentage,
                'resume_url': resume_url,
                'expires_at': draft.expires_at,
            }
        )
        
        draft.recovery_email_sent = True
        draft.recovery_email_sent_at = timezone.now()
        draft.save()
```

---

### 3.7 Organizer-Side Registration Verification Checklist

**Verification Checklist Model**:

```python
# tournaments/models.py
class RegistrationVerificationChecklist(models.Model):
    """
    Organizer's checklist for verifying registration.
    Tracks what has been verified.
    """
    registration = models.OneToOneField('Registration', on_delete=models.CASCADE, related_name='verification_checklist')
    
    # Identity Verification
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    game_id_verified = models.BooleanField(default=False)
    
    # Game-Specific Verification
    rank_verified = models.BooleanField(default=False)
    rank_screenshot_approved = models.BooleanField(default=False)
    
    # Team Verification (if team tournament)
    team_roster_verified = models.BooleanField(default=False)
    team_captain_confirmed = models.BooleanField(default=False)
    
    # Payment Verification
    payment_verified = models.BooleanField(default=False)
    payment_proof_approved = models.BooleanField(default=False)
    
    # Document Verification
    all_documents_uploaded = models.BooleanField(default=False)
    all_documents_verified = models.BooleanField(default=False)
    
    # Age Verification (if required)
    age_verified = models.BooleanField(default=False)
    parent_consent_verified = models.BooleanField(default=False)
    
    # Overall Status
    is_fully_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    def calculate_completion_percentage(self) -> int:
        """Calculate verification completion percentage."""
        total_checks = 0
        completed_checks = 0
        
        # Count all boolean fields
        for field in self._meta.get_fields():
            if isinstance(field, models.BooleanField) and field.name != 'is_fully_verified':
                total_checks += 1
                if getattr(self, field.name):
                    completed_checks += 1
        
        return int((completed_checks / total_checks) * 100) if total_checks > 0 else 0
```

---

## 4. Frontend Integration Notes

### 4.1 Registration UI Components

**Component 1: Registration Wizard**

```typescript
// Frontend component specification
interface RegistrationWizardProps {
    tournamentId: number;
    userId: number;
    onComplete: (registrationId: number) => void;
}

interface RegistrationWizardState {
    currentStep: 'player_info' | 'team_info' | 'review' | 'payment';
    formData: Record<string, any>;
    autoFilledFields: string[];
    lockedFields: string[];
    validationErrors: Record<string, string[]>;
    completionPercentage: number;
}

// Events emitted:
// - onStepChange(newStep: string)
// - onSave(draftData: object)
// - onValidationError(field: string, errors: string[])
// - onComplete(registrationId: number)
```

**Component 2: Auto-Fill Display**

```typescript
interface AutoFillFieldDisplayProps {
    fieldName: string;
    value: any;
    source: 'profile' | 'team' | 'game_account';
    isLocked: boolean;
    isVerified: boolean;
    onUnlock?: () => void;  // Only if user has permission
}

// Visual indicators:
// - Green badge: "Auto-filled from Profile ✓"
// - Lock icon: Field locked (verified)
// - Warning icon: Low confidence auto-fill
```

---

### 4.2 Match Reporting UI Components

**Component 1: Result Submission Form**

```typescript
interface ResultSubmissionFormProps {
    matchId: number;
    currentUserId: number;
    gameConfig: GameConfig;  // Schema for result structure
}

interface ResultSubmissionFormState {
    claimedWinner: number;
    scores: Record<string, number>;
    proofScreenshot: File | null;
    notes: string;
    validationErrors: Record<string, string[]>;
}

// Events:
// - onSubmit(submission: MatchResultSubmission)
// - onValidationError(errors: object)
// - onProofUpload(file: File)
```

**Component 2: Results Inbox (Organizer)**

```typescript
interface ResultsInboxProps {
    tournamentId: number;
    filter: 'pending' | 'disputed' | 'conflicted' | 'all';
}

interface ResultInboxItem {
    submissionId: number;
    matchId: number;
    participants: [string, string];  // Team/player names
    claimedWinner: string;
    status: 'pending' | 'confirmed' | 'disputed';
    submittedAt: Date;
    disputeReason?: string;
}

// Actions:
// - Review submission
// - Approve/reject
// - Order rematch
// - Request more info
```

---

### 4.3 Bracket Rendering UI Contracts

**Component: Single-Elimination Bracket Tree**

```typescript
interface BracketTreeProps {
    tournamentId: number;
    rounds: BracketRound[];
    onMatchClick: (matchId: number) => void;
}

interface BracketRound {
    roundNumber: number;
    roundName: string;  // "Quarterfinals", "Semifinals", etc.
    matches: BracketMatch[];
}

interface BracketMatch {
    matchId: number;
    participant1: Participant;
    participant2: Participant;
    winner?: Participant;
    state: 'pending' | 'live' | 'completed';
    scheduledTime?: Date;
}

interface Participant {
    id: number;
    name: string;
    seed?: number;
    score?: number;
}
```

---

### 4.4 Group Stage Table Rendering

**Component: Group Standings Table**

```typescript
interface GroupStandingsProps {
    groupId: number;
    showTiebreakers: boolean;
}

interface GroupStanding {
    rank: number;
    participant: Participant;
    matchesPlayed: number;
    matchesWon: number;
    matchesLost: number;
    roundsWon: number;
    roundsLost: number;
    roundDifferential: number;
    points: number;
    advancementStatus: 'advances' | 'eliminated' | 'pending';
    
    // Tiebreaker indicators
    headToHeadRecord?: string;  // "1-0 vs Team B"
    buchholzScore?: number;  // Swiss system only
}

// Visual indicators:
// - Green highlight: Advances to playoffs
// - Red highlight: Eliminated
// - Trophy icon: Group winner
```

---

### 4.5 Organizer Tools UX

**Dashboard Component**

```typescript
interface OrganizerDashboardProps {
    tournamentId: number;
}

interface DashboardWidgets {
    // Registration Widget
    registrationStats: {
        total: number;
        verified: number;
        pending: number;
        pendingPayment: number;
    };
    
    // Match Results Widget
    resultsQueue: {
        pendingConfirmation: number;
        disputed: number;
        overdue: number;  // Matches past scheduled time with no result
    };
    
    // Bracket Widget
    bracketProgress: {
        roundsCompleted: number;
        roundsTotal: number;
        matchesCompleted: number;
        matchesTotal: number;
    };
    
    // Actions
    quickActions: [
        'Review pending registrations',
        'Resolve disputed results',
        'Edit bracket',
        'Send announcement',
    ];
}
```

---

## 5. Data Flow & Service Boundaries

### 3.1 Service Architecture Overview

**Layered Communication Pattern**:

```
┌───────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                         │
│  ┌────────────────────┐  ┌────────────────────┐              │
│  │  Registration UI   │  │  Registration API  │              │
│  │  (Django Template) │  │  (DRF ViewSet)     │              │
│  └────────────────────┘  └────────────────────┘              │
└────────────────────┬──────────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────────┐
│               ORCHESTRATION LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  TournamentOpsService                                    │ │
│  │   - process_registration_workflow()                      │ │
│  │   - create_draft()                                       │ │
│  │   - submit_registration()                                │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────┬──────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        │            │            │            │
        ▼            ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   Games      │ │  Teams   │ │  Users   │ │ Economy  │
│  Adapter     │ │ Adapter  │ │ Adapter  │ │ Adapter  │
└──────┬───────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
       │              │            │            │
       ▼              ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│GameService   │ │TeamService│ │ProfileSvc│ │WalletSvc │
│GameRulesEngine│ │TeamStatsSvc│ │UserStatsSvc│ │         │
└──────────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

### 3.2 Registration Workflow Data Flow

#### Complete Registration Flow with Service Interactions

```python
# tournaments/services/tournament_ops_service.py
from tournaments.adapters import GameAdapter, TeamAdapter, UserAdapter, EconomyAdapter

class TournamentOpsService:
    """
    Orchestrates complete registration workflow.
    Coordinates between Games, Teams, Users, Economy domains.
    """
    
    @staticmethod
    @transaction.atomic
    def create_registration_draft(
        tournament_id: int,
        user_id: int,
        team_id: int = None
    ) -> RegistrationDraft:
        """
        Step 1: Create draft with auto-fill data.
        
        Service Interactions:
        - GameAdapter: Get identity configs, tournament config
        - UserAdapter: Get user profile data
        - TeamAdapter: Get team data (if team tournament)
        """
        tournament = Tournament.objects.select_related('game').get(id=tournament_id)
        user = User.objects.get(id=user_id)
        
        # 1. Get game configuration (via GameAdapter)
        identity_configs = GameAdapter.get_identity_configs(tournament.game.id)
        tournament_config = GameAdapter.get_tournament_config(
            tournament.game.id,
            tournament.format
        )
        
        # 2. Get user profile data (via UserAdapter)
        user_profile_data = UserAdapter.get_profile_data(user_id)
        
        # 3. Get team data if team tournament (via TeamAdapter)
        team_data = None
        if tournament.is_team_based:
            if not team_id:
                raise ValidationError('Team required for team tournament')
            
            team_data = TeamAdapter.get_team(team_id)
            
            # Check permission
            if not TeamAdapter.check_tournament_permission(user_id, team_id):
                raise PermissionDenied('You do not have permission to register this team')
        
        # 4. Generate auto-fill data
        autofill_service = RegistrationAutoFillService()
        autofill_data = autofill_service.generate_autofill_data(
            user=user,
            tournament=tournament,
            team=team_data
        )
        
        # 5. Create draft
        registration_number = generate_registration_number(tournament)
        
        draft = RegistrationDraft.objects.create(
            user=user,
            tournament=tournament,
            team_id=team_id,
            registration_number=registration_number,
            form_data={
                field_name: field.value
                for field_name, field in autofill_data.items()
            },
            auto_filled_fields=[
                field_name
                for field_name, field in autofill_data.items()
                if field.value
            ],
            locked_fields=[
                field_name
                for field_name, field in autofill_data.items()
                if field.locked
            ],
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        return draft
    
    @staticmethod
    @transaction.atomic
    def submit_registration(
        draft_uuid: str,
        final_form_data: dict,
        payment_method: str = None
    ) -> Registration:
        """
        Step 2: Submit registration (atomic transaction).
        
        Service Interactions:
        - GameAdapter: Validate fields, check eligibility
        - TeamAdapter: Validate team eligibility
        - RegistrationService: Create registration record
        - EconomyAdapter: Process payment (if required)
        - UserAdapter: Update user stats
        - EventBus: Publish RegistrationCompletedEvent
        """
        draft = RegistrationDraft.objects.select_related(
            'tournament__game', 'user', 'team'
        ).get(uuid=draft_uuid)
        
        if draft.submitted:
            raise ValidationError('Registration already submitted')
        
        tournament = draft.tournament
        user = draft.user
        team = draft.team
        
        # 1. Validate all fields (via GameAdapter)
        validation_result = GameAdapter.validate_registration_data(
            game_id=tournament.game.id,
            data=final_form_data
        )
        
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        # 2. Check eligibility (via GameAdapter, TeamAdapter)
        eligibility = RegistrationEligibilityService.check_eligibility(
            tournament=tournament,
            user=user,
            team=team
        )
        
        if not eligibility.is_eligible:
            raise ValidationError(eligibility.reasons)
        
        # 3. Create registration record
        registration = Registration.objects.create(
            tournament=tournament,
            user=user,
            team=team,
            registration_number=draft.registration_number,
            registration_data=final_form_data,
            status=Registration.PENDING_PAYMENT if tournament.has_entry_fee else Registration.CONFIRMED
        )
        
        # 4. Process payment (via EconomyAdapter)
        if tournament.has_entry_fee:
            if payment_method == 'deltacoin':
                # Instant DeltaCoin payment
                try:
                    EconomyAdapter.deduct_entry_fee(
                        user_id=user.id,
                        amount=tournament.entry_fee_amount,
                        reason=f'Tournament registration: {tournament.name}',
                        idempotency_key=f'reg-{registration.id}'
                    )
                    
                    # Payment success → Mark confirmed
                    registration.status = Registration.CONFIRMED
                    registration.save()
                    
                except InsufficientFundsError as e:
                    # Rollback registration
                    registration.delete()
                    raise ValidationError('Insufficient DeltaCoin balance') from e
            
            elif payment_method == 'manual':
                # Manual payment → Create pending payment record
                Payment.objects.create(
                    registration=registration,
                    amount=tournament.entry_fee_amount,
                    payment_method='manual',
                    status=Payment.PENDING
                )
                # Registration stays PENDING_PAYMENT
        
        # 5. Update user stats (via UserAdapter)
        UserAdapter.increment_tournaments_entered(user.id)
        
        # 6. Mark draft as submitted
        draft.submitted = True
        draft.registration = registration
        draft.save()
        
        # 7. Send notification
        NotificationService.send_registration_confirmation(registration)
        
        # 8. Publish event
        events.publish(RegistrationCompletedEvent(
            registration_id=registration.id,
            tournament_id=tournament.id,
            user_id=user.id,
            team_id=team.id if team else None
        ))
        
        return registration
```

---

### 3.3 Adapter Implementations

#### GameAdapter

```python
# tournaments/adapters/game_adapter.py
from games.services import GameService, GameValidationService, GameRulesEngine
from typing import List, Dict, Any

class GameAdapter:
    """
    Adapter for games domain integration.
    Isolates tournaments app from games app implementation.
    """
    
    @staticmethod
    def get_identity_configs(game_id: int) -> List[GamePlayerIdentityConfigDTO]:
        """
        Get identity field configurations for game.
        
        Returns:
            List of DTOs (not model instances) to avoid coupling.
        """
        from games.models import GamePlayerIdentityConfig
        
        configs = GamePlayerIdentityConfig.objects.filter(
            game_id=game_id,
            is_required=True
        ).order_by('display_order')
        
        return [
            GamePlayerIdentityConfigDTO(
                field_name=c.field_name,
                display_label=c.display_label,
                validation_pattern=c.validation_pattern,
                is_required=c.is_required,
                is_immutable=c.is_immutable,
                help_text=c.help_text,
                placeholder=c.placeholder
            )
            for c in configs
        ]
    
    @staticmethod
    def get_tournament_config(game_id: int, format_type: str) -> GameTournamentConfigDTO:
        """Get tournament configuration for game format."""
        from games.models import GameTournamentConfig
        
        config = GameTournamentConfig.objects.get(
            game_id=game_id,
            format_type=format_type
        )
        
        return GameTournamentConfigDTO(
            format_type=config.format_type,
            best_of_options=config.best_of_options,
            scoring_type=config.scoring_type,
            result_schema=config.result_schema,
            default_match_duration_minutes=config.default_match_duration_minutes
        )
    
    @staticmethod
    def validate_registration_data(game_id: int, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate registration data against game identity configs.
        
        Uses GameValidationService from games app.
        """
        return GameValidationService.validate_registration_data(game_id, data)
    
    @staticmethod
    def validate_match_result(
        game_id: int,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> ValidationResult:
        """
        Validate match result using game rules engine.
        """
        from games.models import Game, GameTournamentConfig
        
        game = Game.objects.get(id=game_id)
        tournament_config = GameTournamentConfig.objects.get(
            game=game,
            format_type=tournament_format
        )
        
        is_valid, errors = GameRulesEngine.validate_match_result(
            game=game,
            result_data=result_data,
            tournament_config=tournament_config
        )
        
        return ValidationResult(is_valid=is_valid, errors=errors)
    
    @staticmethod
    def calculate_match_points(
        game_id: int,
        result_data: Dict[str, Any],
        tournament_format: str
    ) -> Dict[str, Decimal]:
        """Calculate tournament points from match result."""
        from games.models import Game
        
        game = Game.objects.get(id=game_id)
        
        return GameRulesEngine.calculate_match_points(
            game=game,
            result_data=result_data,
            tournament_format=tournament_format
        )
```

---

#### TeamAdapter

```python
# tournaments/adapters/team_adapter.py
from teams.services import TeamService, TeamPermissionService

class TeamAdapter:
    """
    Adapter for teams domain integration.
    """
    
    @staticmethod
    def get_team(team_id: int) -> TeamDTO:
        """Get team data without importing Team model."""
        team = TeamService.get_team(team_id)
        
        return TeamDTO(
            id=team.id,
            name=team.name,
            captain_id=team.captain_id,
            captain_name=team.captain.username,
            member_ids=[m.user_id for m in team.members.all()],
            member_names=[m.user.username for m in team.members.all()],
            game=team.game,
            is_verified=team.is_verified,
            logo_url=team.logo.url if team.logo else None
        )
    
    @staticmethod
    def check_tournament_permission(user_id: int, team_id: int) -> bool:
        """
        Check if user can register team for tournaments.
        
        Rules:
        - User must be captain OR
        - User must be member with 'can_register' permission
        """
        return TeamPermissionService.has_tournament_permission(user_id, team_id)
    
    @staticmethod
    def validate_team_eligibility(
        team_id: int,
        tournament_id: int,
        game_id: int,
        required_team_size: int
    ) -> ValidationResult:
        """
        Validate team eligibility for tournament.
        
        Checks:
        - Team game matches tournament game
        - Team size meets requirements
        - All members have required game accounts
        """
        team = TeamService.get_team(team_id)
        errors = []
        
        # Game match
        if team.game_id != game_id:
            errors.append(f'Team is for {team.game.name}, tournament is for different game')
        
        # Team size
        member_count = team.members.count()
        if member_count != required_team_size:
            errors.append(
                f'Team has {member_count} members, tournament requires {required_team_size}'
            )
        
        # Check if team already registered
        from tournaments.models import Registration
        if Registration.objects.filter(tournament_id=tournament_id, team_id=team_id).exists():
            errors.append('Team already registered for this tournament')
        
        return ValidationResult(is_valid=(len(errors) == 0), errors=errors)
    
    @staticmethod
    def get_team_stats(team_id: int) -> TeamStatsDTO:
        """Get team statistics for display."""
        from teams.services import TeamStatsService
        
        stats = TeamStatsService.get_stats(team_id)
        
        return TeamStatsDTO(
            matches_played=stats.matches_played,
            matches_won=stats.matches_won,
            win_rate=stats.win_rate,
            tournaments_participated=stats.tournaments_participated,
            tournaments_won=stats.tournaments_won
        )
```

---

#### UserAdapter

```python
# tournaments/adapters/user_adapter.py
from user_profile.services import ProfileService, UserStatsService

class UserAdapter:
    """
    Adapter for user/profile domain integration.
    """
    
    @staticmethod
    def get_profile_data(user_id: int) -> UserProfileDTO:
        """Get user profile data for auto-fill."""
        profile = ProfileService.get_profile(user_id)
        
        return UserProfileDTO(
            email=profile.user.email,
            email_verified=profile.user.email_verified,
            phone=profile.phone,
            phone_verified=profile.phone_verified,
            discord=profile.discord,
            riot_id=profile.riot_id,
            steam_id=profile.steam_id,
            pubg_mobile_id=profile.pubg_mobile_id,
            # ... other game IDs
            age=profile.age,
            region=profile.region,
        )
    
    @staticmethod
    def check_user_verification(user_id: int) -> UserVerificationDTO:
        """Check user verification status."""
        profile = ProfileService.get_profile(user_id)
        
        return UserVerificationDTO(
            email_verified=profile.user.email_verified,
            phone_verified=profile.phone_verified,
            riot_account_verified=bool(profile.riot_id),  # TODO: Add OAuth verification
            steam_account_verified=bool(profile.steam_id),
        )
    
    @staticmethod
    def increment_tournaments_entered(user_id: int):
        """Update user stats after registration."""
        UserStatsService.increment_tournaments_entered(user_id)
    
    @staticmethod
    def get_user_stats(user_id: int) -> UserStatsDTO:
        """Get user tournament statistics."""
        stats = UserStatsService.get_stats(user_id)
        
        return UserStatsDTO(
            tournaments_entered=stats.tournaments_entered,
            tournaments_completed=stats.tournaments_completed,
            tournaments_won=stats.tournaments_won,
            matches_played=stats.matches_played,
            matches_won=stats.matches_won,
            win_rate=stats.win_rate,
            total_deltacoin_earned=stats.total_deltacoin_earned
        )
```

---

#### EconomyAdapter

```python
# tournaments/adapters/economy_adapter.py
from economy.services import WalletService, TransactionService

class EconomyAdapter:
    """
    Adapter for economy domain integration.
    Handles DeltaCoin wallet operations.
    """
    
    @staticmethod
    def get_balance(user_id: int) -> Decimal:
        """Get user's DeltaCoin balance."""
        return WalletService.get_balance(user_id)
    
    @staticmethod
    def deduct_entry_fee(
        user_id: int,
        amount: Decimal,
        reason: str,
        idempotency_key: str
    ):
        """
        Deduct entry fee from user's wallet.
        
        Raises:
            InsufficientFundsError: If balance too low
        """
        return WalletService.deduct_funds(
            user_id=user_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key
        )
    
    @staticmethod
    def add_prize(
        user_id: int,
        amount: Decimal,
        reason: str,
        idempotency_key: str
    ):
        """Award prize to user's wallet."""
        return WalletService.add_funds(
            user_id=user_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key
        )
    
    @staticmethod
    def refund_entry_fee(
        user_id: int,
        original_transaction_id: int,
        reason: str
    ):
        """Refund entry fee (e.g., tournament cancelled)."""
        return TransactionService.refund_transaction(
            transaction_id=original_transaction_id,
            reason=reason
        )
```

---

### 3.4 Data Flow Diagrams

#### Flow 1: Registration Draft Creation

```
User (Frontend)
    │
    │ POST /api/tournaments/vct-2025/registrations/drafts/
    ▼
TournamentOpsService.create_registration_draft()
    │
    ├──> GameAdapter.get_identity_configs(game_id)
    │    │
    │    └──> GameService (games app)
    │         └──> Returns: [riot_id config, discord config, ...]
    │
    ├──> UserAdapter.get_profile_data(user_id)
    │    │
    │    └──> ProfileService (user_profile app)
    │         └──> Returns: {email, phone, riot_id, discord, ...}
    │
    ├──> TeamAdapter.get_team(team_id) [if team tournament]
    │    │
    │    └──> TeamService (teams app)
    │         └──> Returns: {name, captain, members, ...}
    │
    ├──> RegistrationAutoFillService.generate_autofill_data()
    │    └──> Combines: Game configs + User profile + Team data
    │         └──> Returns: {field_name: AutoFillField(value, locked, verified)}
    │
    └──> Create RegistrationDraft (database)
         └──> Returns: {uuid, registration_number, autofill_data, locked_fields}
```

---

#### Flow 2: Registration Submission

```
User (Frontend)
    │
    │ POST /api/registrations/drafts/{uuid}/submit/
    │ Body: {final_form_data, payment_method: "deltacoin"}
    ▼
TournamentOpsService.submit_registration()
    │
    ├──> GameAdapter.validate_registration_data()
    │    │
    │    └──> GameValidationService (games app)
    │         └──> Validates: Riot ID format, required fields, etc.
    │         └──> Returns: {is_valid, errors}
    │
    ├──> RegistrationEligibilityService.check_eligibility()
    │    ├──> GameAdapter: Check game-specific rules (rank, region)
    │    ├──> TeamAdapter: Check team eligibility (size, game match)
    │    └──> UserAdapter: Check verification status
    │         └──> Returns: {is_eligible, reasons}
    │
    ├──> Create Registration (database)
    │    └──> Status: PENDING_PAYMENT
    │
    ├──> EconomyAdapter.deduct_entry_fee()
    │    │
    │    └──> WalletService (economy app)
    │         ├──> Check balance
    │         ├──> Deduct funds (atomic)
    │         ├──> Create transaction record
    │         └──> Returns: Transaction{id, amount, ...}
    │
    ├──> Update Registration
    │    └──> Status: CONFIRMED (payment success)
    │
    ├──> UserAdapter.increment_tournaments_entered()
    │    │
    │    └──> UserStatsService (user_profile app)
    │         └──> Increment tournaments_entered counter
    │
    ├──> NotificationService.send_confirmation()
    │    └──> Email: Registration details + receipt
    │
    └──> EventBus.publish(RegistrationCompletedEvent)
         └──> Async handlers:
              - Update leaderboards
              - Send Discord notification
              - Update analytics
```

---

#### Flow 3: Match Result Validation (Using Game Rules)

```
Organizer/Participant (Frontend)
    │
    │ POST /api/matches/{id}/submit-result/
    │ Body: {
    │   team1_rounds: 13,
    │   team2_rounds: 7,
    │   map_name: "Haven"
    │ }
    ▼
MatchService.submit_result()
    │
    ├──> GameAdapter.validate_match_result()
    │    │
    │    └──> GameRulesEngine (games app)
    │         ├──> Load rules module: valorant_rules.py
    │         ├──> Call: rules.validate_match_result()
    │         │    └──> Check: Rounds 0-25, winner has 13+, etc.
    │         └──> Returns: {is_valid, errors}
    │
    ├──> GameAdapter.calculate_match_points() [if Swiss/RR]
    │    │
    │    └──> GameRulesEngine
    │         ├──> Load rules module: valorant_rules.py
    │         ├──> Call: rules.calculate_match_points()
    │         │    └──> Winner: 3pts, Loser: 0pts, Round diff: +6
    │         └──> Returns: {team1_points: 3, team2_points: 0}
    │
    ├──> Determine winner
    │    └──> GameRulesEngine.get_rules(game).determine_winner()
    │         └──> Returns: 1 (team1 wins)
    │
    ├──> Update Match (database)
    │    ├──> result_data = {...} (JSONB)
    │    ├──> winner_participant = 1
    │    └──> state = PENDING_RESULT
    │
    └──> EventBus.publish(MatchResultSubmittedEvent)
         └──> Async handler: Notify opponent to confirm
```

---

### 3.5 Service Boundary Rules

**Communication Rules Matrix**:

| From Domain | To Domain | Allowed Method | Example |
|-------------|-----------|----------------|---------|
| Tournaments | Games | Adapter (sync) | Get game configs, validate results |
| Tournaments | Teams | Adapter (sync) | Get team data, check permissions |
| Tournaments | Users | Adapter (sync) | Get profile data, check verification |
| Tournaments | Economy | Adapter (sync) | Deduct entry fee, award prizes |
| Tournaments | Leaderboards | Event (async) | Update rankings after tournament |
| Games | Tournaments | ❌ **FORBIDDEN** | Games app should not know about tournaments |
| Teams | Tournaments | ❌ **FORBIDDEN** | Teams app should not know about tournaments |
| Economy | Tournaments | ❌ **FORBIDDEN** | Economy app should not know about tournaments |

**Why One-Way Dependencies?**:
- ✅ Core domains (Games, Teams, Users, Economy) remain independent
- ✅ Easy to extract core domains into separate microservices later
- ✅ Clear ownership: Tournaments orchestrates, core domains provide services
- ✅ No circular dependencies

---

### 3.6 DTO (Data Transfer Object) Patterns

**Why DTOs?**:
- ✅ Avoid exposing model internals across domains
- ✅ Clear API contracts (breaking changes visible)
- ✅ Easy to mock in tests (no Django model dependencies)
- ✅ Type-safe (can use dataclasses, Pydantic)

**Example DTOs**:

```python
# tournaments/adapters/dtos.py
from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

@dataclass
class GamePlayerIdentityConfigDTO:
    """DTO for game identity configuration."""
    field_name: str
    display_label: str
    validation_pattern: Optional[str]
    is_required: bool
    is_immutable: bool
    help_text: str
    placeholder: str

@dataclass
class TeamDTO:
    """DTO for team data."""
    id: int
    name: str
    captain_id: int
    captain_name: str
    member_ids: List[int]
    member_names: List[str]
    game: str  # Game slug
    is_verified: bool
    logo_url: Optional[str]

@dataclass
class UserProfileDTO:
    """DTO for user profile data."""
    email: str
    email_verified: bool
    phone: Optional[str]
    phone_verified: bool
    discord: Optional[str]
    riot_id: Optional[str]
    steam_id: Optional[str]
    pubg_mobile_id: Optional[str]
    age: Optional[int]
    region: Optional[str]

@dataclass
class ValidationResult:
    """Generic validation result DTO."""
    is_valid: bool
    errors: List[str]
```

---

### 3.7 Organizer Tools for Registration Management

**Admin Dashboard Features**:

1. **Registration Overview**:
   - Total registrations: 45 / 64 slots
   - Confirmed: 40
   - Pending payment: 5
   - Withdrawn: 2
   - Revenue: $450 collected, $50 pending

2. **Registration List** (Filterable):
   ```
   | Reg # | Player/Team | Status | Payment | Registered |
   |-------|-------------|--------|---------|------------|
   | VCT-2025-001234 | Player#1234 | ✅ CONFIRMED | DeltaCoin | 2h ago |
   | VCT-2025-001235 | TeamX | ⏳ PENDING | Manual | 1h ago |
   | VCT-2025-001236 | Player#5678 | ❌ WITHDRAWN | Refunded | 3h ago |
   ```

3. **Bulk Actions**:
   - Export registrations (CSV, Excel)
   - Send bulk email to participants
   - Approve/reject pending payments (bulk)
   - Cancel registrations (with refund)

4. **Payment Review Queue**:
   - View uploaded payment proofs
   - Approve/reject with comments
   - Auto-notify user on decision

5. **Eligibility Overrides**:
   - Manually approve ineligible registrations (with reason)
   - Set custom entry fee for specific users (scholarship, sponsor)

---

## 6. Implementation Roadmap

### Phase 1: Game Rules Layer (Weeks 1-3)

**Tasks**:
1. Create models: `GamePlayerIdentityConfig`, `GameTournamentConfig`, `GameScoringRule`
2. Migrate existing game data to config tables
3. Implement `GameRulesEngine` and `DefaultGameRules`
4. Create custom rules modules for 2-3 games (Valorant, PUBG, CS2)
5. Update match result submission to use rules engine

**Deliverables**:
- ✅ All 11 games configured via database
- ✅ Match result validation driven by config
- ✅ Points calculation driven by config/rules modules

---

### Phase 2: Smart Registration - Core (Weeks 4-6)

**Tasks**:
1. Create `RegistrationDraft` model
2. Implement `RegistrationAutoFillService`
3. Create registration draft API endpoints (create, update, submit)
4. Build registration wizard UI with auto-fill
5. Implement field locking (lock verified fields)

**Deliverables**:
- ✅ Draft persistence with UUID-based resume
- ✅ Auto-fill from user profile + team + game configs
- ✅ Unique registration numbers
- ✅ Field locking for verified fields

---

### Phase 3: Adapters & Service Boundaries (Weeks 7-8)

**Tasks**:
1. Create adapters: `GameAdapter`, `TeamAdapter`, `UserAdapter`, `EconomyAdapter`
2. Define DTOs for cross-domain communication
3. Refactor existing registration code to use adapters
4. Remove all direct model imports (Games, Teams, Users from Tournaments app)

**Deliverables**:
- ✅ All cross-domain communication via adapters
- ✅ DTOs defined for all adapter methods
- ✅ Zero direct model imports across domains

---

### Phase 4: Advanced Features (Weeks 9-10)

**Tasks**:
1. Implement real-time validation API (`POST /api/validate-field/`)
2. Build organizer registration management dashboard
3. Add payment review queue UI
4. Implement bulk actions (export, email, approve)
5. Add eligibility override system

**Deliverables**:
- ✅ Real-time field validation as user types
- ✅ Organizer can manage all registrations
- ✅ Payment review workflow
- ✅ Bulk operations

---

## 7. Summary

### Key Design Decisions

1. **Configuration-Driven Games**:
   - All game-specific behavior in database config
   - Pluggable rules modules for complex logic
   - Add new games without code deployment

2. **Manual Result Verification Pipeline**:
   - 6-step workflow: Submit → Opponent Confirm/Dispute → Organizer Review → TournamentOps Validate → Event Propagation → Stats Update
   - Multi-checkpoint verification (no game API dependency)
   - Proof screenshots required for all submissions
   - Dispute mechanism with organizer resolution
   - Schema validation + game rules validation
   - Event-driven stats updates

3. **Smart Registration (Enhanced)**:
   - Auto-fill from multiple sources (profile, team, game configs)
   - Field locking for verified data (prevent fraud)
   - Draft persistence for cross-device resume
   - Unique registration numbers for tracking
   - **Game-aware questions**: Dynamic fields based on game/format
   - **Conditional inputs**: Show/hide fields based on selections
   - **Document requirements**: Required screenshots/uploads (rank proof, ID, parent consent)
   - **Draft recovery**: Email reminders, cross-device resume, UUID-based recovery
   - **Organizer verification checklist**: Track verification progress (identity, rank, payment, documents)

4. **Frontend Integration Contracts**:
   - Registration wizard with multi-step flow
   - Auto-fill display with lock/verify indicators
   - Result submission form with proof upload
   - Results Inbox for organizers (pending/disputed queue)
   - Bracket rendering (single-elim, group stage, Swiss)
   - Group standings with tiebreaker indicators
   - Organizer dashboard with quick actions

5. **Clean Architecture**:
   - Adapters for all cross-domain communication
   - DTOs to avoid model coupling
   - One-way dependencies (Tournaments → Core Domains)
   - Event-driven updates (no manual calls)

6. **Game-Agnostic Tournament System**:
   - Works for all 11 games via configuration
   - Supports multiple formats (Single/Double Elim, Swiss, Round Robin, Group→Knockout)
   - Flexible scoring (Win/Loss, Rounds, Kills+Placement, Time-based, Custom)
   - Validation driven by game rules engine + JSON Schema

### Benefits

**For Developers**:
- ✅ Add new games via config (no code changes)
- ✅ Clear service boundaries (easy to test, refactor)
- ✅ Game-agnostic codebase (no hardcoded logic)
- ✅ Frontend contracts defined (consistent UI development)

**For Users**:
- ✅ Fast registration (auto-fill from profile)
- ✅ Safe registration (verified fields locked)
- ✅ Resume anytime (draft persistence, email recovery)
- ✅ Clear tracking (registration numbers)
- ✅ Easy result submission (guided workflow with proof upload)

**For Organizers**:
- ✅ Easy registration management (admin dashboard, verification checklist)
- ✅ Payment review workflow (approve/reject)
- ✅ Result verification inbox (pending/disputed queue)
- ✅ Dispute resolution tools (approve/reject/rematch)
- ✅ Bulk operations (export, email)
- ✅ Flexible eligibility (overrides, custom fees)
- ✅ Comprehensive audit trail (all submissions/decisions logged)

### Document Structure

**Section 1**: Game Rules Layer
- Game configuration models
- Rules engine architecture
- Scoring systems (group-based, Swiss, PUBG, time-based)
- Match schema validation

**Section 2**: Result Input Pipeline (No Game APIs)
- 6-step manual verification workflow
- MatchResultSubmission + DisputeRecord models
- TournamentOps services (submission, verification, finalization)
- Event-driven stats propagation

**Section 3**: Smart Registration (Expanded)
- Registration draft model
- Auto-fill intelligence
- Game-aware questions
- Conditional field display
- Document requirements
- Draft recovery
- Organizer verification checklist

**Section 4**: Frontend Integration Notes
- Registration UI components
- Match reporting components
- Bracket rendering contracts
- Group stage tables
- Organizer dashboard UX

**Section 5**: Data Flow & Service Boundaries
- Service architecture
- Adapter patterns
- DTO specifications
- Cross-domain communication

**Section 6**: Implementation Roadmap
- 9-week phased delivery
- Game rules → Registration → Testing

**Section 7**: Summary (this section)

---

**End of Smart Registration & Game Rules Design**
