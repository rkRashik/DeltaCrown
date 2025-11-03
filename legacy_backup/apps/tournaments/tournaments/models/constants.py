# apps/tournaments/models/constants.py

# Legacy tournament status choices (kept for compatibility)
STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("PUBLISHED", "Published"),
    ("RUNNING", "Running"),
    ("COMPLETED", "Completed"),
]

# Payment methods used by registration forms (ChoiceField expects list of 2-tuples)
# Wallet rails are the primary ones; keep labels user-friendly for the UI.
PAYMENT_METHODS = [
    ("bkash", "bKash"),
    ("nagad", "Nagad"),
    ("rocket", "Rocket"),
    # Optional rails often referenced in admin/settings; safe to include here:
    ("bank", "Bank Transfer"),
    ("cash", "Cash on site"),
]
