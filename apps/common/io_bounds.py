"""Explicit, opt-in I/O contracts. No settings/env wiring or production defaults.

Socket limits apply per attempt/inactivity, not to a whole synchronous operation.
These helpers do not interrupt owning threads, force-close DB connections, or
promise pooler/COMMIT/ROLLBACK deadlines. Provider parity requires staging.
"""
from contextlib import contextmanager
import math


def _positive(value):
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError("Explicit positive finite limit required")
    return value


def _count(value, *, minimum):
    if type(value) is not int or value < minimum:
        raise ValueError("Explicit finite integer count required")
    return value


@contextmanager
def transaction_timeouts(*, statement_ms, lock_ms, using="default"):
    """Own one selected transaction; SET LOCAL ends on commit or rollback.

    Refuse nesting: releasing a savepoint would not end a SET LOCAL setting.
    This is not an application-wide transaction or a total transaction deadline.
    """
    from django.db import connections, transaction
    _count(statement_ms, minimum=1)
    _count(lock_ms, minimum=1)
    if lock_ms >= statement_ms:
        raise ValueError("Lock limit must precede statement limit")
    connection = connections[using]
    if connection.in_atomic_block or not connection.get_autocommit():
        raise RuntimeError("Timeout scope must own its transaction")
    with transaction.atomic(using=using):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('statement_timeout', %s, true), "
                           "set_config('lock_timeout', %s, true)",
                           [str(statement_ms), str(lock_ms)])
        yield


def redis_socket_options(*, connect_seconds, read_seconds, max_connections, retries, asynchronous=False):
    """Existing redis-py retry types, explicit finite attempts, no backoff.

    Non-blocking pool exhaustion is distinct from its async internal-lock wait.
    A caller-owned async deadline can bound an await; no thread timeout is added.
    """
    from redis.backoff import NoBackoff
    if asynchronous:
        from redis.asyncio.retry import Retry
    else:
        from redis.retry import Retry
    return dict(socket_connect_timeout=_positive(connect_seconds), socket_timeout=_positive(read_seconds),
                max_connections=_count(max_connections, minimum=1),
                retry=Retry(NoBackoff(), _count(retries, minimum=0)))


def channels_redis_host(address, **limits):
    """Use Channels' supported host-dict path, not RedisCache backend OPTIONS."""
    from channels_redis.core import RedisChannelLayer
    options = redis_socket_options(**limits, asynchronous=True)
    if options["socket_timeout"] <= RedisChannelLayer.brpop_timeout:
        raise ValueError("Read limit must allow Channels' ordinary blocking receive interval")
    return dict(address=address, **options)


def s3_socket_config(*, connect_seconds, read_seconds, attempts):
    """Pre-response SDK retry budget; streaming body reads are not replayed."""
    from botocore.config import Config
    return Config(connect_timeout=_positive(connect_seconds), read_timeout=_positive(read_seconds),
                  s3={"addressing_style": "path"},
                  retries={"mode":"standard", "total_max_attempts":_count(attempts, minimum=1)})
