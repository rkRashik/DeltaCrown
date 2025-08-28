# deltacrown/settings_test_pg.py
from .settings import *

# Force Django to use the precreated DB name for tests
DATABASES["default"]["TEST"] = {"NAME": "deltacrown_test"}
