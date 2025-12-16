import os
import sys
# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
import django
django.setup()

from django.test.client import RequestFactory
from django.contrib.auth import get_user_model
from apps.user_profile.views_public import public_profile

User = get_user_model()

def main(username='rkrashik'):
    rf = RequestFactory()
    user = User.objects.filter(username=username).first()
    if not user:
        print('User not found:', username)
        return
    request = rf.get(f'/u/{username}/')
    # attach anonymous user
    request.user = type('U', (), {'is_authenticated': False})()
    resp = public_profile(request, username)
    print('Status:', getattr(resp, 'status_code', 'rendered'))

if __name__ == '__main__':
    main()
