"""
Seed Form Builder Templates
Management command to create system form templates

Usage:
    python manage.py seed_form_templates
"""
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tournaments.models import RegistrationFormTemplate, Game

User = get_user_model()


class Command(BaseCommand):
    help = 'Create system form templates for tournaments'

    def handle(self, *args, **options):
        """Create seed templates"""
        self.stdout.write("Creating system form templates...")
        
        # Get or create system user
        system_user, _ = User.objects.get_or_create(
            username='system',
            defaults={'email': 'system@deltacrown.gg', 'is_staff': True}
        )
        
        templates_created = 0
        
        # 1. Valorant Solo Registration Template
        valorant_game = Game.objects.filter(name__icontains='valorant').first()
        valorant_solo_schema = {
            "sections": [
                {
                    "id": "player_info",
                    "title": "Player Information",
                    "fields": [
                        {
                            "id": "in_game_name",
                            "type": "text",
                            "label": "In-Game Name (IGN)",
                            "required": True,
                            "placeholder": "Your Valorant IGN",
                            "validation": {
                                "min_length": 3,
                                "max_length": 16,
                                "pattern": "^[a-zA-Z0-9_]+$",
                                "error_message": "IGN must be 3-16 characters (letters, numbers, underscore only)"
                            }
                        },
                        {
                            "id": "riot_id",
                            "type": "text",
                            "label": "Riot ID (with tagline)",
                            "required": True,
                            "placeholder": "Example: PlayerName#APAC",
                            "validation": {
                                "pattern": "^[^#]+#[^#]+$",
                                "error_message": "Format: YourName#TAG"
                            }
                        },
                        {
                            "id": "rank",
                            "type": "dropdown",
                            "label": "Current Rank",
                            "required": True,
                            "options": [
                                "Iron", "Bronze", "Silver", "Gold", 
                                "Platinum", "Diamond", "Ascendant", 
                                "Immortal", "Radiant"
                            ]
                        },
                        {
                            "id": "server_region",
                            "type": "dropdown",
                            "label": "Server Region",
                            "required": True,
                            "options": ["Singapore", "Mumbai", "Hong Kong", "Tokyo"]
                        }
                    ]
                },
                {
                    "id": "contact_info",
                    "title": "Contact Information",
                    "fields": [
                        {
                            "id": "email",
                            "type": "email",
                            "label": "Email Address",
                            "required": True,
                            "placeholder": "your.email@example.com"
                        },
                        {
                            "id": "phone",
                            "type": "phone",
                            "label": "Phone Number",
                            "required": True,
                            "placeholder": "+8801XXXXXXXXX",
                            "validation": {
                                "region": "BD"
                            }
                        },
                        {
                            "id": "discord",
                            "type": "text",
                            "label": "Discord Username",
                            "required": True,
                            "placeholder": "username#1234"
                        }
                    ]
                },
                {
                    "id": "agreements",
                    "title": "Rules & Agreements",
                    "fields": [
                        {
                            "id": "age_verification",
                            "type": "checkbox",
                            "label": "Age Verification",
                            "required": True,
                            "options": ["I confirm that I am 16 years or older"]
                        },
                        {
                            "id": "rules_agreement",
                            "type": "agreement",
                            "label": "I have read and agree to the tournament rules and code of conduct",
                            "required": True,
                            "description": "By checking this box, you acknowledge that you have read and accept all tournament rules"
                        },
                        {
                            "id": "anti_cheat_agreement",
                            "type": "agreement",
                            "label": "I agree to play fair and will not use any cheats or exploits",
                            "required": True
                        }
                    ]
                }
            ]
        }
        
        valorant_template, created = RegistrationFormTemplate.objects.update_or_create(
            slug='valorant-solo-apac',
            defaults={
                'name': 'Valorant Solo APAC Registration',
                'description': 'Standard solo player registration form for Valorant tournaments in APAC region',
                'participation_type': 'solo',
                'game': valorant_game,
                'form_schema': valorant_solo_schema,
                'is_system_template': True,
                'is_featured': True,
                'is_active': True,
                'created_by': system_user,
                'tags': ['valorant', 'solo', 'apac', 'competitive']
            }
        )
        if created:
            templates_created += 1
            self.stdout.write(self.style.SUCCESS(f"✓ Created: {valorant_template.name}"))
        
        # 2. PUBG Mobile Team Registration Template
        pubg_game = Game.objects.filter(name__icontains='pubg').first()
        pubg_team_schema = {
            "sections": [
                {
                    "id": "team_info",
                    "title": "Team Information",
                    "fields": [
                        {
                            "id": "team_name",
                            "type": "text",
                            "label": "Team Name",
                            "required": True,
                            "placeholder": "Enter your team name",
                            "validation": {
                                "min_length": 3,
                                "max_length": 30
                            }
                        },
                        {
                            "id": "team_tag",
                            "type": "text",
                            "label": "Team Tag/Abbreviation",
                            "required": True,
                            "placeholder": "TM (2-5 characters)",
                            "validation": {
                                "min_length": 2,
                                "max_length": 5,
                                "pattern": "^[A-Z0-9]+$",
                                "error_message": "Tag must be uppercase letters/numbers only"
                            }
                        },
                        {
                            "id": "team_logo",
                            "type": "file",
                            "label": "Team Logo (Optional)",
                            "required": False,
                            "validation": {
                                "max_size_mb": 2,
                                "allowed_types": [".png", ".jpg", ".jpeg"]
                            }
                        }
                    ]
                },
                {
                    "id": "captain_info",
                    "title": "Team Captain Information",
                    "fields": [
                        {
                            "id": "captain_ign",
                            "type": "text",
                            "label": "Captain In-Game Name",
                            "required": True,
                            "validation": {
                                "min_length": 3,
                                "max_length": 16
                            }
                        },
                        {
                            "id": "captain_uid",
                            "type": "number",
                            "label": "Captain PUBG UID",
                            "required": True,
                            "validation": {
                                "min_value": 10000000,
                                "integer_only": True
                            }
                        },
                        {
                            "id": "captain_phone",
                            "type": "phone",
                            "label": "Captain Phone Number",
                            "required": True,
                            "validation": {
                                "region": "BD"
                            }
                        },
                        {
                            "id": "captain_email",
                            "type": "email",
                            "label": "Captain Email",
                            "required": True
                        }
                    ]
                },
                {
                    "id": "players",
                    "title": "Team Roster (6 Players: 4 Main + 2 Substitutes)",
                    "fields": [
                        {
                            "id": "section_header_main",
                            "type": "section_header",
                            "label": "Main Players (4)"
                        },
                        {
                            "id": "player_1_ign",
                            "type": "text",
                            "label": "Player 1 IGN",
                            "required": True
                        },
                        {
                            "id": "player_1_uid",
                            "type": "number",
                            "label": "Player 1 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "player_2_ign",
                            "type": "text",
                            "label": "Player 2 IGN",
                            "required": True
                        },
                        {
                            "id": "player_2_uid",
                            "type": "number",
                            "label": "Player 2 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "player_3_ign",
                            "type": "text",
                            "label": "Player 3 IGN",
                            "required": True
                        },
                        {
                            "id": "player_3_uid",
                            "type": "number",
                            "label": "Player 3 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "player_4_ign",
                            "type": "text",
                            "label": "Player 4 IGN",
                            "required": True
                        },
                        {
                            "id": "player_4_uid",
                            "type": "number",
                            "label": "Player 4 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "divider_subs",
                            "type": "divider"
                        },
                        {
                            "id": "section_header_subs",
                            "type": "section_header",
                            "label": "Substitute Players (2)"
                        },
                        {
                            "id": "sub_1_ign",
                            "type": "text",
                            "label": "Substitute 1 IGN",
                            "required": True
                        },
                        {
                            "id": "sub_1_uid",
                            "type": "number",
                            "label": "Substitute 1 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "sub_2_ign",
                            "type": "text",
                            "label": "Substitute 2 IGN",
                            "required": True
                        },
                        {
                            "id": "sub_2_uid",
                            "type": "number",
                            "label": "Substitute 2 UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        }
                    ]
                },
                {
                    "id": "agreements",
                    "title": "Rules & Agreements",
                    "fields": [
                        {
                            "id": "rules_agreement",
                            "type": "agreement",
                            "label": "I confirm all team members agree to tournament rules",
                            "required": True
                        },
                        {
                            "id": "fair_play",
                            "type": "agreement",
                            "label": "We will play fair and report any issues to tournament organizers",
                            "required": True
                        }
                    ]
                }
            ]
        }
        
        pubg_template, created = RegistrationFormTemplate.objects.update_or_create(
            slug='pubg-mobile-team-bd',
            defaults={
                'name': 'PUBG Mobile Team Bangladesh',
                'description': 'Team registration form for PUBG Mobile tournaments (4+2 roster)',
                'participation_type': 'team',
                'game': pubg_game,
                'form_schema': pubg_team_schema,
                'is_system_template': True,
                'is_featured': True,
                'is_active': True,
                'created_by': system_user,
                'tags': ['pubg', 'mobile', 'team', 'bangladesh']
            }
        )
        if created:
            templates_created += 1
            self.stdout.write(self.style.SUCCESS(f"✓ Created: {pubg_template.name}"))
        
        # 3. Free Fire Solo Quick Registration
        freefire_game = Game.objects.filter(name__icontains='free fire').first()
        freefire_schema = {
            "sections": [
                {
                    "id": "player_info",
                    "title": "Player Details",
                    "fields": [
                        {
                            "id": "ff_ign",
                            "type": "text",
                            "label": "Free Fire IGN",
                            "required": True,
                            "validation": {"min_length": 3, "max_length": 20}
                        },
                        {
                            "id": "ff_uid",
                            "type": "number",
                            "label": "Free Fire UID",
                            "required": True,
                            "validation": {"integer_only": True}
                        },
                        {
                            "id": "phone",
                            "type": "phone",
                            "label": "Phone Number",
                            "required": True,
                            "validation": {"region": "BD"}
                        },
                        {
                            "id": "level",
                            "type": "dropdown",
                            "label": "Account Level",
                            "required": True,
                            "options": ["1-30", "31-50", "51-70", "71+"]
                        }
                    ]
                },
                {
                    "id": "agreements",
                    "title": "Quick Agreement",
                    "fields": [
                        {
                            "id": "rules_accept",
                            "type": "agreement",
                            "label": "I agree to tournament rules and fair play policy",
                            "required": True
                        }
                    ]
                }
            ]
        }
        
        freefire_template, created = RegistrationFormTemplate.objects.update_or_create(
            slug='free-fire-solo-quick',
            defaults={
                'name': 'Free Fire Solo Quick Entry',
                'description': 'Quick registration form for Free Fire solo tournaments',
                'participation_type': 'solo',
                'game': freefire_game,
                'form_schema': freefire_schema,
                'is_system_template': True,
                'is_featured': True,
                'is_active': True,
                'created_by': system_user,
                'tags': ['freefire', 'solo', 'quick', 'bangladesh']
            }
        )
        if created:
            templates_created += 1
            self.stdout.write(self.style.SUCCESS(f"✓ Created: {freefire_template.name}"))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {templates_created} new system templates"))
        self.stdout.write(self.style.SUCCESS(f"📊 Total templates in database: {RegistrationFormTemplate.objects.count()}"))
