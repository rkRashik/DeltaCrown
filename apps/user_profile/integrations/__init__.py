"""
User Profile Integrations

This package contains integration modules for connecting User Profile system
with other platform domains (tournaments, economy, moderation, etc.).

All integrations are feature-flag guarded and designed to be:
- Non-breaking (don't change existing behavior)
- Idempotent (safe to call multiple times)
- Lightweight (defer heavy computation)
"""
