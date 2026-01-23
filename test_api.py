import requests
import json

# Test the games API
r = requests.get('http://127.0.0.1:8000/profile/api/games/')
data = r.json()

# Find VALORANT
valorant = [g for g in data['games'] if g['slug'] == 'valorant'][0]

print(f'\nVALORANT API Response:')
print(f'  Total fields: {len(valorant["passport_schema"])}')
print('\nFields:')
for f in valorant['passport_schema']:
    opts = f' ({len(f.get("options", []))} options)' if f.get('options') else ''
    print(f'  - {f["label"]} ({f["key"]}): type={f["type"]}, required={f["required"]}{opts}')

print('\n\nFull JSON for first field:')
print(json.dumps(valorant['passport_schema'][0], indent=2))
