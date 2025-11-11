"""
Economy App Exceptions

Implements: Documents/ExecutionPlan/MODULE_7.1_KICKOFF.md - Step 2
Custom exceptions for coin system operations.
"""


class InvalidAmount(ValueError):
    """
    Raised when transaction amount is invalid (zero, negative for credit, etc).
    
    Examples:
        - credit(amount=0) → InvalidAmount
        - credit(amount=-50) → InvalidAmount
        - debit(amount=0) → InvalidAmount
    """
    pass


class InsufficientFunds(ValueError):
    """
    Raised when debit exceeds available balance without overdraft permission.
    
    Example:
        Wallet balance: 50 coins
        Debit attempt: 100 coins
        allow_overdraft: False
        → InsufficientFunds("Insufficient balance: 50 available, 100 required")
    """
    pass


class InvalidWallet(ValueError):
    """
    Raised when wallet operation references invalid or non-existent wallet.
    
    Examples:
        - transfer(from_profile=A, to_profile=A) → InvalidWallet("Cannot transfer to self")
        - operation on deleted/soft-deleted wallet → InvalidWallet
    """
    pass


class IdempotencyConflict(ValueError):
    """
    Raised when duplicate idempotency_key is used with different parameters.
    
    Example:
        First call:  credit(amount=100, key="ABC")
        Second call: credit(amount=200, key="ABC")
        → IdempotencyConflict("Key 'ABC' already used with different amount: 100 vs 200")
    
    Note: This is a safety check to prevent accidental key reuse.
    Duplicate calls with identical parameters return the original transaction (idempotent).
    """
    pass
