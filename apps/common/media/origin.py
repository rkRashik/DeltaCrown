"""Bounded access to the private object store (OL-10, hardened in OL-12).

Incident evidence (Render, 8 Nov): unbounded concurrent S3 reads against Supabase Storage filled the
10-connection pool ("Connection pool is full"), media requests took 2.5-24 s, and the health probe timed
out behind them. Every origin read needs a lease from one process-wide budget; a request that cannot get one
within a few seconds is shed with a fast 503 + Retry-After instead of piling up threads and memory.

OL-12 production finding: a burst of cancelled requests left every lease unreleased (a response dropped by a
disconnected client is only finalised by the garbage collector, which an idle service does not run), so all
media returned the "busy" 503 until restart. Therefore:
  * a lease can never be held longer than MAX_HOLD_SECONDS: expired leases are reclaimed by the next acquirer,
    independent of garbage collection (a late release of a reclaimed lease is a no-op);
  * small immutable derivatives are read completely under the lease and released at once (no streaming
    lifecycle at all), and recently served ones come from a small bounded in-memory cache without any origin
    read.
Nothing here weakens authorization: leases and the cache are used only after the caller has authorized the record.
"""
import logging
import os
import threading
import time
import weakref
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)

SLOTS = max(1, int(os.getenv("MEDIA_ORIGIN_CONCURRENCY", "3")))  # originals, streamed to the client
SMALL_SLOTS = max(1, int(os.getenv("MEDIA_ORIGIN_SMALL_CONCURRENCY", "8")))  # derivative requests (auth + small read)
WAIT_SECONDS = float(os.getenv("MEDIA_ORIGIN_WAIT_SECONDS", "5"))
MAX_HOLD_SECONDS = float(os.getenv("MEDIA_ORIGIN_MAX_HOLD_SECONDS", "45"))
SMALL_WAIT_SECONDS = float(os.getenv("MEDIA_ORIGIN_SMALL_WAIT_SECONDS", "10"))  # a cold page fetches ~50 at once
MAX_WAITERS = 24  # beyond this, shed immediately: waiting requests each hold a thread
SMALL_MAX_WAITERS = 64
CHUNK = 256 * 1024  # fewer thread hops per image than 64 KiB
SMALL_OBJECT_BYTES = 768 * 1024  # derivatives are read whole up to this size (they are ~10-300 KiB)

pool = ThreadPoolExecutor(max_workers=SLOTS, thread_name_prefix="media-origin")
_slots = threading.BoundedSemaphore(SLOTS)
_small_slots = threading.BoundedSemaphore(SMALL_SLOTS)  # SLOTS + SMALL_SLOTS (11) fits the S3 pool of 12
_lock = threading.Lock()
_waiting = {False: 0, True: 0}  # requests currently waiting for a slot, per budget
_active = {}  # id(cell) -> cell, for the leases currently holding a slot


class Lease:
    """One origin slot; releasing twice is harmless and a garbage-collected lease frees its slot too."""

    def __init__(self, sem=None):
        self._cell = [False, time.monotonic(), sem or _slots]  # [released, taken_at, semaphore]
        with _lock:
            _active[id(self._cell)] = self._cell
        weakref.finalize(self, _release_once, self._cell)

    def release(self):
        _release_once(self._cell)


def _release_once(cell):
    with _lock:
        if cell[0]:
            return
        cell[0] = True
        _active.pop(id(cell), None)
    cell[2].release()


def _reap():
    """Reclaim slots whose holder is gone (cancelled request, dropped response): bounded hold, no GC needed."""
    now, expired = time.monotonic(), []
    with _lock:
        for key, cell in list(_active.items()):
            if now - cell[1] > MAX_HOLD_SECONDS and not cell[0]:
                expired.append(cell)
    for cell in expired:
        log.warning("media origin lease reclaimed after %ss", int(MAX_HOLD_SECONDS))
        _release_once(cell)


def acquire(small=False):
    """Blocking (call from a sync request thread). A Lease, or None when the origin budget is exhausted.

    `small=True` is for objects read completely and released at once (derivatives): a separate, larger budget.
    """
    sem = _small_slots if small else _slots
    with _lock:
        if _waiting[small] >= (SMALL_MAX_WAITERS if small else MAX_WAITERS):
            return None
        _waiting[small] += 1
    try:
        deadline = time.monotonic() + (SMALL_WAIT_SECONDS if small else WAIT_SECONDS)
        while True:
            _reap()
            left = deadline - time.monotonic()
            if sem.acquire(timeout=max(0.0, min(1.0, left))):
                return Lease(sem)
            if left <= 1.0:
                return None
    finally:
        with _lock:
            _waiting[small] -= 1


# --- tiny bounded cache for immutable derivative bytes -------------------------------------------------------
CACHE_BYTES = int(os.getenv("MEDIA_DERIVATIVE_CACHE_BYTES", str(6 * 1024 * 1024)))  # well under the 512 MiB budget
CACHE_ENTRY_MAX = 256 * 1024
_cache = OrderedDict()
_cache_size = 0
_cache_lock = threading.Lock()


def cache_get(key):
    with _cache_lock:
        data = _cache.get(key)
        if data is not None:
            _cache.move_to_end(key)
        return data


def cache_put(key, data):
    """Keys embed the record id and the content version, so an entry can never become wrong, only unused."""
    global _cache_size
    if len(data) > CACHE_ENTRY_MAX or CACHE_BYTES <= 0:
        return
    with _cache_lock:
        old = _cache.pop(key, None)
        if old is not None:
            _cache_size -= len(old)
        _cache[key] = data
        _cache_size += len(data)
        while _cache_size > CACHE_BYTES and _cache:
            _, dropped = _cache.popitem(last=False)
            _cache_size -= len(dropped)


_storage_warmed = False


def warm_storage():
    """Build the private S3 client once at boot (local work, no network call). Otherwise the first burst after a
    deploy makes every concurrent request thread construct its own boto3 session on a 0.15 vCPU instance."""
    global _storage_warmed
    if _storage_warmed:
        return
    _storage_warmed = True
    try:
        from django.core.files.storage import storages
        storage = storages["private_media"]
        getattr(storage, "bucket", None)
    except Exception:  # not configured (legacy/local mode): nothing to warm
        log.debug("media storage warm-up skipped", exc_info=True)
