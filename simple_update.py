import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

# Update each game individually
print("\n=== Updating Ranks ===\n")

# Valorant
game = Game.objects.get(name='VALORANT')
game.available_ranks = [
    {'value': 'iron_1', 'label': 'Iron 1'}, {'value': 'iron_2', 'label': 'Iron 2'}, {'value': 'iron_3', 'label': 'Iron 3'},
    {'value': 'bronze_1', 'label': 'Bronze 1'}, {'value': 'bronze_2', 'label': 'Bronze 2'}, {'value': 'bronze_3', 'label': 'Bronze 3'},
    {'value': 'silver_1', 'label': 'Silver 1'}, {'value': 'silver_2', 'label': 'Silver 2'}, {'value': 'silver_3', 'label': 'Silver 3'},
    {'value': 'gold_1', 'label': 'Gold 1'}, {'value': 'gold_2', 'label': 'Gold 2'}, {'value': 'gold_3', 'label': 'Gold 3'},
    {'value': 'platinum_1', 'label': 'Platinum 1'}, {'value': 'platinum_2', 'label': 'Platinum 2'}, {'value': 'platinum_3', 'label': 'Platinum 3'},
    {'value': 'diamond_1', 'label': 'Diamond 1'}, {'value': 'diamond_2', 'label': 'Diamond 2'}, {'value': 'diamond_3', 'label': 'Diamond 3'},
    {'value': 'ascendant_1', 'label': 'Ascendant 1'}, {'value': 'ascendant_2', 'label': 'Ascendant 2'}, {'value': 'ascendant_3', 'label': 'Ascendant 3'},
    {'value': 'immortal_1', 'label': 'Immortal 1'}, {'value': 'immortal_2', 'label': 'Immortal 2'}, {'value': 'immortal_3', 'label': 'Immortal 3'},
    {'value': 'radiant', 'label': 'Radiant'},
]
game.save()
print(f"OK VALORANT: 25 ranks")

# CS2
game = Game.objects.get(name='Counter-Strike 2')
game.available_ranks = [
    {'value': 'silver_1', 'label': 'Silver 1'}, {'value': 'silver_2', 'label': 'Silver 2'}, {'value': 'silver_3', 'label': 'Silver 3'}, {'value': 'silver_4', 'label': 'Silver 4'},
    {'value': 'silver_elite', 'label': 'Silver Elite'}, {'value': 'silver_elite_master', 'label': 'Silver Elite Master'},
    {'value': 'gold_nova_1', 'label': 'Gold Nova 1'}, {'value': 'gold_nova_2', 'label': 'Gold Nova 2'}, {'value': 'gold_nova_3', 'label': 'Gold Nova 3'}, {'value': 'gold_nova_master', 'label': 'Gold Nova Master'},
    {'value': 'master_guardian_1', 'label': 'Master Guardian I'}, {'value': 'master_guardian_2', 'label': 'Master Guardian II'}, {'value': 'master_guardian_elite', 'label': 'Master Guardian Elite'},
    {'value': 'distinguished_master_guardian', 'label': 'Distinguished Master Guardian'},
    {'value': 'legendary_eagle', 'label': 'Legendary Eagle'}, {'value': 'legendary_eagle_master', 'label': 'Legendary Eagle Master'},
    {'value': 'supreme_master_first_class', 'label': 'Supreme Master First Class'}, {'value': 'the_global_elite', 'label': 'The Global Elite'},
]
game.save()
print(f"OK Counter-Strike 2: 18 ranks")

# Dota 2
game = Game.objects.get(name='Dota 2')
game.available_ranks = [
    {'value': 'herald', 'label': 'Herald'}, {'value': 'guardian', 'label': 'Guardian'}, {'value': 'crusader', 'label': 'Crusader'},
    {'value': 'archon', 'label': 'Archon'}, {'value': 'legend', 'label': 'Legend'}, {'value': 'ancient', 'label': 'Ancient'},
    {'value': 'divine', 'label': 'Divine'}, {'value': 'immortal', 'label': 'Immortal'},
]
game.save()
print(f"OK Dota 2: 8 ranks")

# PUBG Mobile
game = Game.objects.get(name='PUBG MOBILE')
game.available_ranks = [
    {'value': 'bronze', 'label': 'Bronze'}, {'value': 'silver', 'label': 'Silver'}, {'value': 'gold', 'label': 'Gold'},
    {'value': 'platinum', 'label': 'Platinum'}, {'value': 'diamond', 'label': 'Diamond'}, {'value': 'crown', 'label': 'Crown'},
    {'value': 'ace', 'label': 'Ace'}, {'value': 'ace_master', 'label': 'Ace Master'}, {'value': 'ace_dominator', 'label': 'Ace Dominator'},
    {'value': 'conqueror', 'label': 'Conqueror'},
]
game.save()
print(f"OK PUBG MOBILE: 10 ranks")

# Mobile Legends
game = Game.objects.get(name='Mobile Legends: Bang Bang')
game.available_ranks = [
    {'value': 'warrior', 'label': 'Warrior'}, {'value': 'elite', 'label': 'Elite'}, {'value': 'master', 'label': 'Master'},
    {'value': 'grandmaster', 'label': 'Grandmaster'}, {'value': 'epic', 'label': 'Epic'}, {'value': 'legend', 'label': 'Legend'},
    {'value': 'mythic', 'label': 'Mythic'}, {'value': 'mythic_honor', 'label': 'Mythic Honor'},
    {'value': 'mythic_glory', 'label': 'Mythic Glory'}, {'value': 'mythic_immortal', 'label': 'Mythic Immortal'},
]
game.save()
print(f"OK Mobile Legends: 10 ranks")

# Free Fire
game = Game.objects.get(name='Free Fire')
game.available_ranks = [
    {'value': 'bronze', 'label': 'Bronze'}, {'value': 'silver', 'label': 'Silver'}, {'value': 'gold', 'label': 'Gold'},
    {'value': 'platinum', 'label': 'Platinum'}, {'value': 'diamond', 'label': 'Diamond'}, {'value': 'heroic', 'label': 'Heroic'},
    {'value': 'grandmaster', 'label': 'Grandmaster'},
]
game.save()
print(f"OK Free Fire: 7 ranks")

# COD Mobile (no special characters)
game = Game.objects.get(short_code='CODM')
game.available_ranks = [
    {'value': 'rookie', 'label': 'Rookie'}, {'value': 'veteran', 'label': 'Veteran'}, {'value': 'elite', 'label': 'Elite'},
    {'value': 'pro', 'label': 'Pro'}, {'value': 'master', 'label': 'Master'}, {'value': 'grandmaster', 'label': 'Grandmaster'},
    {'value': 'legendary', 'label': 'Legendary'},
]
game.save()
print(f"OK Call of Duty Mobile: 7 ranks")

# Rocket League
game = Game.objects.get(name='Rocket League')
game.available_ranks = [
    {'value': 'bronze_1', 'label': 'Bronze I'}, {'value': 'bronze_2', 'label': 'Bronze II'}, {'value': 'bronze_3', 'label': 'Bronze III'},
    {'value': 'silver_1', 'label': 'Silver I'}, {'value': 'silver_2', 'label': 'Silver II'}, {'value': 'silver_3', 'label': 'Silver III'},
    {'value': 'gold_1', 'label': 'Gold I'}, {'value': 'gold_2', 'label': 'Gold II'}, {'value': 'gold_3', 'label': 'Gold III'},
    {'value': 'platinum_1', 'label': 'Platinum I'}, {'value': 'platinum_2', 'label': 'Platinum II'}, {'value': 'platinum_3', 'label': 'Platinum III'},
    {'value': 'diamond_1', 'label': 'Diamond I'}, {'value': 'diamond_2', 'label': 'Diamond II'}, {'value': 'diamond_3', 'label': 'Diamond III'},
    {'value': 'champion_1', 'label': 'Champion I'}, {'value': 'champion_2', 'label': 'Champion II'}, {'value': 'champion_3', 'label': 'Champion III'},
    {'value': 'grand_champion_1', 'label': 'Grand Champion I'}, {'value': 'grand_champion_2', 'label': 'Grand Champion II'}, {'value': 'grand_champion_3', 'label': 'Grand Champion III'},
    {'value': 'supersonic_legend', 'label': 'Supersonic Legend'},
]
game.save()
print(f"OK Rocket League: 22 ranks")

# Rainbow Six (using short_code)
game = Game.objects.get(short_code='R6')
game.available_ranks = [
    {'value': 'copper_5', 'label': 'Copper V'}, {'value': 'copper_4', 'label': 'Copper IV'}, {'value': 'copper_3', 'label': 'Copper III'}, {'value': 'copper_2', 'label': 'Copper II'}, {'value': 'copper_1', 'label': 'Copper I'},
    {'value': 'bronze_5', 'label': 'Bronze V'}, {'value': 'bronze_4', 'label': 'Bronze IV'}, {'value': 'bronze_3', 'label': 'Bronze III'}, {'value': 'bronze_2', 'label': 'Bronze II'}, {'value': 'bronze_1', 'label': 'Bronze I'},
    {'value': 'silver_5', 'label': 'Silver V'}, {'value': 'silver_4', 'label': 'Silver IV'}, {'value': 'silver_3', 'label': 'Silver III'}, {'value': 'silver_2', 'label': 'Silver II'}, {'value': 'silver_1', 'label': 'Silver I'},
    {'value': 'gold_3', 'label': 'Gold III'}, {'value': 'gold_2', 'label': 'Gold II'}, {'value': 'gold_1', 'label': 'Gold I'},
    {'value': 'platinum_3', 'label': 'Platinum III'}, {'value': 'platinum_2', 'label': 'Platinum II'}, {'value': 'platinum_1', 'label': 'Platinum I'},
    {'value': 'emerald_3', 'label': 'Emerald III'}, {'value': 'emerald_2', 'label': 'Emerald II'}, {'value': 'emerald_1', 'label': 'Emerald I'},
    {'value': 'diamond_3', 'label': 'Diamond III'}, {'value': 'diamond_2', 'label': 'Diamond II'}, {'value': 'diamond_1', 'label': 'Diamond I'},
    {'value': 'champion', 'label': 'Champion'},
]
game.save()
print(f"OK Rainbow Six Siege: 28 ranks")

# EA FC (using short_code)
game = Game.objects.get(short_code='FC26')
game.available_ranks = [
    {'value': 'division_10', 'label': 'Division 10'}, {'value': 'division_9', 'label': 'Division 9'}, {'value': 'division_8', 'label': 'Division 8'},
    {'value': 'division_7', 'label': 'Division 7'}, {'value': 'division_6', 'label': 'Division 6'}, {'value': 'division_5', 'label': 'Division 5'},
    {'value': 'division_4', 'label': 'Division 4'}, {'value': 'division_3', 'label': 'Division 3'}, {'value': 'division_2', 'label': 'Division 2'},
    {'value': 'division_1', 'label': 'Division 1'}, {'value': 'elite_division', 'label': 'Elite Division'},
]
game.save()
print(f"OK EA SPORTS FC 26: 11 ranks")

# eFootball (using short_code)
game = Game.objects.get(short_code='EFB')
game.available_ranks = [
    {'value': 'beginner', 'label': 'Beginner'}, {'value': 'amateur', 'label': 'Amateur'}, {'value': 'intermediate', 'label': 'Intermediate'},
    {'value': 'advanced', 'label': 'Advanced'}, {'value': 'professional', 'label': 'Professional'}, {'value': 'expert', 'label': 'Expert'},
    {'value': 'champion', 'label': 'Champion'},
]
game.save()
print(f"OK eFootball 2026: 7 ranks")

print("\n=== COMPLETE! All 11 games updated with 2025 ranks ===\n")
