from apps.games.models import Game
from apps.user_profile.models import GamePassportSchema
import json

# Check Valorant schema
game = Game.objects.get(name='Valorant')
print(f"Game: {game.name} (slug: {game.slug})")

try:
    schema = GamePassportSchema.objects.get(game=game)
    print(f"\nSchema found!")
    print(f"  Identity fields: {json.dumps(schema.identity_fields, indent=2)}")
    print(f"  Display format: {schema.display_format}")
    print(f"  Required fields: {schema.get_required_identity_fields()}")
except GamePassportSchema.DoesNotExist:
    print(f"\n❌ No schema found for {game.name}!")
    print("This game needs a schema to be created.")
