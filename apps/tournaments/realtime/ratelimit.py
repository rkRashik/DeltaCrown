"""
Rate Limiting Utilities for WebSocket Connections

Token-bucket algorithm backed by Redis for production, fallback to in-memory
for development. Prevents abuse while allowing legitimate bursts.

Phase 2: Real-Time Features & Security
Module 2.5: Rate Limiting & Abuse Protection

Implements:
- check_and_consume(user_id, key, rate_per_sec, burst) - Per-user message throttling
- check_and_consume_ip(ip, key, rate_per_sec, burst) - Per-IP throttling
- room_try_join(room, user_id, max_members) - Room capacity limits

Redis Keys:
- ws:msg:{user_id} - Message rate tracking
- ws:conn:{user_id} - Connection count tracking
- ws:ip:{ip} - IP-based rate tracking
- ws:room:{tournament_id} - Room membership tracking

Uses LUA scripts for atomic operations; graceful degradation if Redis unavailable.
"""

import logging
import time
from typing import Optional, Tuple
from collections import defaultdict, deque
from threading import Lock

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Redis LUA Scripts (Atomic Token Bucket)
# =============================================================================

# Token bucket algorithm: replenish tokens at fixed rate, consume on request
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local rate = tonumber(ARGV[1])          -- tokens per second
local burst = tonumber(ARGV[2])         -- max tokens (bucket capacity)
local now = tonumber(ARGV[3])           -- current timestamp (milliseconds)
local cost = tonumber(ARGV[4])          -- tokens to consume (usually 1)

-- Get current state (last_refill_time, tokens)
local state = redis.call('HMGET', key, 'last_refill', 'tokens')
local last_refill = tonumber(state[1]) or now
local tokens = tonumber(state[2]) or burst

-- Calculate tokens to add since last refill
local elapsed = (now - last_refill) / 1000.0  -- convert to seconds
local tokens_to_add = elapsed * rate
tokens = math.min(burst, tokens + tokens_to_add)

-- Try to consume
if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'last_refill', now, 'tokens', tokens)
    redis.call('EXPIRE', key, 3600)  -- 1 hour TTL
    return {1, math.floor(tokens)}  -- success, remaining tokens
else
    -- Calculate retry_after (milliseconds until enough tokens)
    local tokens_needed = cost - tokens
    local retry_after = math.ceil((tokens_needed / rate) * 1000)
    return {0, retry_after}  -- failure, retry_after_ms
end
"""

# Room membership tracking (set-based)
ROOM_TRY_JOIN_LUA = """
local room_key = KEYS[1]
local user_id = ARGV[1]
local max_members = tonumber(ARGV[2])

-- Check current size
local current_size = redis.call('SCARD', room_key)

-- Check if already member
local is_member = redis.call('SISMEMBER', room_key, user_id)

if is_member == 1 then
    return {1, current_size}  -- already member, success
elseif current_size < max_members then
    redis.call('SADD', room_key, user_id)
    redis.call('EXPIRE', room_key, 86400)  -- 24 hour TTL
    return {1, current_size + 1}  -- joined successfully
else
    return {0, current_size}  -- room full
end
"""


# =============================================================================
# In-Memory Fallback (Development Only)
# =============================================================================

class InMemoryRateLimiter:
    """
    Fallback rate limiter when Redis unavailable.
    
    WARNING: Only suitable for single-process development.
    Does NOT work with multiple Daphne/worker processes.
    """
    
    def __init__(self):
        self.buckets = {}  # key -> {last_refill: float, tokens: float}
        self.rooms = defaultdict(set)  # room_key -> set(user_ids)
        self.lock = Lock()
    
    def check_and_consume(
        self,
        key: str,
        rate_per_sec: float,
        burst: int,
        cost: int = 1
    ) -> Tuple[bool, int]:
        """Token bucket algorithm (in-memory)."""
        with self.lock:
            now = time.time()
            
            if key not in self.buckets:
                self.buckets[key] = {'last_refill': now, 'tokens': burst}
            
            bucket = self.buckets[key]
            
            # Refill tokens
            elapsed = now - bucket['last_refill']
            tokens_to_add = elapsed * rate_per_sec
            bucket['tokens'] = min(burst, bucket['tokens'] + tokens_to_add)
            bucket['last_refill'] = now
            
            # Try consume
            if bucket['tokens'] >= cost:
                bucket['tokens'] -= cost
                return True, int(bucket['tokens'])
            else:
                tokens_needed = cost - bucket['tokens']
                retry_after_ms = int((tokens_needed / rate_per_sec) * 1000)
                return False, retry_after_ms
    
    def room_try_join(self, room_key: str, user_id: str, max_members: int) -> Tuple[bool, int]:
        """Check room capacity (in-memory)."""
        with self.lock:
            room_members = self.rooms[room_key]
            
            if user_id in room_members:
                return True, len(room_members)  # Already member
            
            if len(room_members) < max_members:
                room_members.add(user_id)
                return True, len(room_members)
            else:
                return False, len(room_members)  # Room full
    
    def room_leave(self, room_key: str, user_id: str):
        """Remove user from room."""
        with self.lock:
            self.rooms[room_key].discard(user_id)
            
            # Clean up empty rooms
            if not self.rooms[room_key]:
                del self.rooms[room_key]


# Global fallback instance
_fallback_limiter = InMemoryRateLimiter()


# =============================================================================
# Redis-Backed Rate Limiting Functions
# =============================================================================

def _use_redis() -> bool:
    """Check if Redis is available and configured."""
    try:
        # Test Redis connection
        cache.set('_ratelimit_test', 1, timeout=1)
        return cache.get('_ratelimit_test') == 1
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
        return False


def check_and_consume(
    user_id: int,
    key_suffix: str,
    rate_per_sec: float,
    burst: int,
    cost: int = 1
) -> Tuple[bool, int]:
    """
    Check and consume rate limit tokens for a user.
    
    Uses token bucket algorithm:
    - Tokens refill at `rate_per_sec` tokens per second
    - Maximum `burst` tokens can accumulate
    - Each request consumes `cost` tokens (default 1)
    
    Args:
        user_id: User ID for rate limiting
        key_suffix: Key suffix (e.g., 'msg', 'conn')
        rate_per_sec: Token refill rate per second
        burst: Maximum tokens (bucket capacity)
        cost: Tokens to consume (default 1)
    
    Returns:
        Tuple[allowed: bool, info: int]
        - If allowed=True: info = remaining tokens
        - If allowed=False: info = retry_after_ms
    
    Examples:
        # Check if user can send message (10 msg/sec, burst 20)
        allowed, remaining = check_and_consume(
            user_id=user.id,
            key_suffix='msg',
            rate_per_sec=10.0,
            burst=20
        )
        
        if not allowed:
            retry_after_ms = remaining
            # Reject with retry_after
    """
    key = f"ws:{key_suffix}:{user_id}"
    
    if _use_redis():
        try:
            # Execute LUA script atomically
            now_ms = int(time.time() * 1000)
            result = cache.client.get_client().eval(
                TOKEN_BUCKET_LUA,
                1,  # number of keys
                key,
                rate_per_sec,
                burst,
                now_ms,
                cost
            )
            
            allowed = bool(result[0])
            info = int(result[1])
            return allowed, info
        
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}", exc_info=True)
            # Fall through to in-memory
    
    # Fallback to in-memory
    return _fallback_limiter.check_and_consume(key, rate_per_sec, burst, cost)


def check_and_consume_ip(
    ip_address: str,
    key_suffix: str,
    rate_per_sec: float,
    burst: int,
    cost: int = 1
) -> Tuple[bool, int]:
    """
    Check and consume rate limit tokens for an IP address.
    
    Same as check_and_consume but keyed by IP instead of user ID.
    Useful for anonymous/unauthenticated connections.
    
    Args:
        ip_address: Client IP address
        key_suffix: Key suffix (e.g., 'msg', 'conn')
        rate_per_sec: Token refill rate per second
        burst: Maximum tokens (bucket capacity)
        cost: Tokens to consume (default 1)
    
    Returns:
        Tuple[allowed: bool, info: int]
        - If allowed=True: info = remaining tokens
        - If allowed=False: info = retry_after_ms
    
    Examples:
        # Check if IP can connect (max 10 connections)
        allowed, remaining = check_and_consume_ip(
            ip_address='192.168.1.100',
            key_suffix='conn',
            rate_per_sec=0.1,  # 1 per 10 seconds
            burst=10
        )
    """
    key = f"ws:ip:{key_suffix}:{ip_address}"
    
    if _use_redis():
        try:
            now_ms = int(time.time() * 1000)
            result = cache.client.get_client().eval(
                TOKEN_BUCKET_LUA,
                1,
                key,
                rate_per_sec,
                burst,
                now_ms,
                cost
            )
            
            allowed = bool(result[0])
            info = int(result[1])
            return allowed, info
        
        except Exception as e:
            logger.error(f"Redis IP rate limit error: {e}", exc_info=True)
    
    # Fallback
    return _fallback_limiter.check_and_consume(key, rate_per_sec, burst, cost)


def room_try_join(room: str, user_id: int, max_members: int) -> Tuple[bool, int]:
    """
    Check if user can join a room (capacity limit).
    
    Args:
        room: Room identifier (e.g., tournament_id)
        user_id: User ID attempting to join
        max_members: Maximum allowed members in room
    
    Returns:
        Tuple[allowed: bool, current_size: int]
        - allowed=True: User joined successfully (or already member)
        - allowed=False: Room at capacity
        - current_size: Current room size after join attempt
    
    Examples:
        # Check if user can join tournament room (max 2000 spectators)
        allowed, room_size = room_try_join(
            room=f"tournament_{tournament.id}",
            user_id=user.id,
            max_members=2000
        )
        
        if not allowed:
            # Reject connection (room full)
    """
    room_key = f"ws:room:{room}"
    user_key = str(user_id)
    
    if _use_redis():
        try:
            result = cache.client.get_client().eval(
                ROOM_TRY_JOIN_LUA,
                1,
                room_key,
                user_key,
                max_members
            )
            
            allowed = bool(result[0])
            room_size = int(result[1])
            return allowed, room_size
        
        except Exception as e:
            logger.error(f"Redis room join error: {e}", exc_info=True)
    
    # Fallback
    return _fallback_limiter.room_try_join(room_key, user_key, max_members)


def room_leave(room: str, user_id: int):
    """
    Remove user from room (on disconnect).
    
    Args:
        room: Room identifier
        user_id: User ID to remove
    """
    room_key = f"ws:room:{room}"
    user_key = str(user_id)
    
    if _use_redis():
        try:
            cache.client.get_client().srem(room_key, user_key)
            return
        except Exception as e:
            logger.error(f"Redis room leave error: {e}", exc_info=True)
    
    # Fallback
    _fallback_limiter.room_leave(room_key, user_key)


def get_room_size(room: str) -> int:
    """
    Get current room size.
    
    Args:
        room: Room identifier
    
    Returns:
        Current number of members in room
    """
    room_key = f"ws:room:{room}"
    
    if _use_redis():
        try:
            return cache.client.get_client().scard(room_key)
        except Exception as e:
            logger.error(f"Redis room size error: {e}", exc_info=True)
    
    # Fallback
    with _fallback_limiter.lock:
        return len(_fallback_limiter.rooms.get(room_key, set()))


# =============================================================================
# Connection Tracking
# =============================================================================

def increment_user_connections(user_id: int) -> int:
    """
    Increment user's active connection count.
    
    Returns:
        Current connection count (after increment)
    """
    key = f"ws:conn:count:{user_id}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().incr(key)
            cache.client.get_client().expire(key, 3600)  # 1 hour TTL
            return count
        except Exception as e:
            logger.error(f"Redis connection increment error: {e}", exc_info=True)
    
    # Fallback (not ideal for multi-process, but better than nothing)
    current = cache.get(key, 0)
    cache.set(key, current + 1, timeout=3600)
    return current + 1


def decrement_user_connections(user_id: int) -> int:
    """
    Decrement user's active connection count.
    
    Returns:
        Current connection count (after decrement)
    """
    key = f"ws:conn:count:{user_id}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().decr(key)
            if count <= 0:
                cache.client.get_client().delete(key)
                return 0
            return count
        except Exception as e:
            logger.error(f"Redis connection decrement error: {e}", exc_info=True)
    
    # Fallback
    current = cache.get(key, 1)
    new_count = max(0, current - 1)
    if new_count > 0:
        cache.set(key, new_count, timeout=3600)
    else:
        cache.delete(key)
    return new_count


def get_user_connections(user_id: int) -> int:
    """
    Get user's current connection count.
    
    Returns:
        Number of active connections
    """
    key = f"ws:conn:count:{user_id}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Redis connection count error: {e}", exc_info=True)
    
    # Fallback
    return cache.get(key, 0)


# =============================================================================
# IP Connection Tracking
# =============================================================================

def increment_ip_connections(ip_address: str) -> int:
    """Increment IP's active connection count."""
    key = f"ws:conn:ip:{ip_address}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().incr(key)
            cache.client.get_client().expire(key, 3600)
            return count
        except Exception as e:
            logger.error(f"Redis IP connection increment error: {e}", exc_info=True)
    
    current = cache.get(key, 0)
    cache.set(key, current + 1, timeout=3600)
    return current + 1


def decrement_ip_connections(ip_address: str) -> int:
    """Decrement IP's active connection count."""
    key = f"ws:conn:ip:{ip_address}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().decr(key)
            if count <= 0:
                cache.client.get_client().delete(key)
                return 0
            return count
        except Exception as e:
            logger.error(f"Redis IP connection decrement error: {e}", exc_info=True)
    
    current = cache.get(key, 1)
    new_count = max(0, current - 1)
    if new_count > 0:
        cache.set(key, new_count, timeout=3600)
    else:
        cache.delete(key)
    return new_count


def get_ip_connections(ip_address: str) -> int:
    """Get IP's current connection count."""
    key = f"ws:conn:ip:{ip_address}"
    
    if _use_redis():
        try:
            count = cache.client.get_client().get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Redis IP connection count error: {e}", exc_info=True)
    
    return cache.get(key, 0)
