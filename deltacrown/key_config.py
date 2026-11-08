"""Parsing and validation for rotation-related key lists read from the environment.

Values are secrets: nothing here may put a key, or any part of one, into an error message.
"""
import json

from django.core.exceptions import ImproperlyConfigured

MAX_KEYS = 5


def parse_key_list(raw, name, *, current=None):
    """Return a list of non-empty strings from a JSON-array env value ("" or unset -> []).

    The format is a JSON array (not comma separated) because keys may contain commas.
    ``current`` (the active key) is dropped if present: a fallback equal to it is pointless.
    """
    if raw is None or not raw.strip():
        return []
    fail = ImproperlyConfigured(f'{name} must be a JSON array of non-empty strings, e.g. ["previous-key"].')
    try:
        value = json.loads(raw)
    except ValueError:
        raise fail from None
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise fail
    keys = [item for item in dict.fromkeys(value) if item != current]
    if len(keys) > MAX_KEYS:
        raise ImproperlyConfigured(f"{name} may list at most {MAX_KEYS} keys; remove retired keys.")
    return keys
