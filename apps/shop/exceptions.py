"""
DeltaCoin Shop Exceptions - Module 7.2

Custom exceptions for spend authorization flows.
"""


class ShopException(Exception):
    """Base exception for shop operations."""
    pass


class InvalidStateTransition(ShopException):
    """Attempted invalid state transition (e.g., capture already-captured hold)."""
    pass


class HoldExpired(ShopException):
    """Hold has expired and cannot be captured."""
    pass


class InvalidTransaction(ShopException):
    """Invalid transaction reference (e.g., refund non-purchase transaction)."""
    pass


class HoldNotFound(ShopException):
    """Hold does not exist or does not belong to wallet."""
    pass


class InsufficientFunds(ShopException):
    """Insufficient available balance for authorization."""
    pass


class InvalidAmount(ShopException):
    """Invalid amount (e.g., zero, negative, exceeds original)."""
    pass


class ItemNotFound(ShopException):
    """Shop item does not exist."""
    pass


class ItemNotActive(ShopException):
    """Shop item is not active for purchase."""
    pass


class IdempotencyConflict(ShopException):
    """Idempotency key conflict with different operation or payload."""
    pass
