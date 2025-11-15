import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

c = Client()
User = get_user_model()

# Login
c.login(username='player', password='testpass123')

# Step 1 -> Step 2
r1 = c.post('/tournaments/test-tournament/register/', {
    'action': 'next',
    'current_step': 1
})
print(f'Step 1->2: {r1.status_code}')
print(f'  Context step: {r1.context.get("current_step") if r1.status_code == 200 else "N/A"}')

# Step 2 -> Step 3
r2 = c.post('/tournaments/test-tournament/register/', {
    'action': 'next',
    'current_step': 2,
    'in_game_id': 'player123'
})
print(f'Step 2->3: {r2.status_code}')
print(f'  Context step: {r2.context.get("current_step") if r2.status_code == 200 else "N/A"}')
print(f'  Is final step: {r2.context.get("is_final_step") if r2.status_code == 200 else "N/A"}')

# Step 3 submit
r3 = c.post('/tournaments/test-tournament/register/', {
    'action': 'submit',
    'current_step': 3,
    'agree_terms': 'on'
})
print(f'Step 3 submit: {r3.status_code}')
if r3.status_code == 200:
    print(f'  Context step: {r3.context.get("current_step")}')
    print(f'  Errors: {r3.context.get("errors")}')
    print(f'  Content snippet: {r3.content[:300]}')
else:
    print(f'  Redirect URL: {r3.get("Location", "No location header")}')
