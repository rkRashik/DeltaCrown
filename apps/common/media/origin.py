"""Bounded access to the private object store (OL-10).

Incident evidence (Render, 8 Nov): unbounded concurrent S3 reads against Supabase Storage filled the
10-connection pool ("Connection pool is full"), media requests took 2.5-24 s, and the health probe timed
out behind them. Every origin read now needs a lease from one process-wide budget; a request that cannot
get one within a few seconds is shed with a fast 503 + Retry-After instead of piling up threads and memory.
Chunk reads use their own small executor, never the 2-thread default one that the rest of Daphne shares.
Nothing here weakens authorization: leases are taken only after the caller has authorized the record.
"""
import os
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor

SLOTS = max(1, int(os.getenv("MEDIA_ORIGIN_CONCURRENCY", "3")))
WAIT_SECONDS = float(os.getenv("MEDIA_ORIGIN_WAIT_SECONDS", "8"))
MAX_WAITERS = 24  # beyond this, shed immediately: waiting requests each hold a thread
CHUNK = 256 * 1024  # fewer thread hops per image than 64 KiB

pool = ThreadPoolExecutor(max_workers=SLOTS, thread_name_prefix="media-origin")
_slots = threading.BoundedSemaphore(SLOTS)
_lock = threading.Lock()
_waiting = 0


class Lease:
    """One origin slot; releasing twice is harmless and a garbage-collected lease can never leak its slot."""

    def __init__(self):
        self._cell = [False]
        weakref.finalize(self, _release_once, self._cell)

    def release(self):
        _release_once(self._cell)


def _release_once(cell):
    with _lock:
        if cell[0]:
            return
        cell[0] = True
    _slots.release()


def acquire():
    """Blocking (call from a sync request thread). A Lease, or None when the origin budget is exhausted."""
    global _waiting
    with _lock:
        if _waiting >= MAX_WAITERS:
            return None
        _waiting += 1
    try:
        got = _slots.acquire(timeout=WAIT_SECONDS)
    finally:
        with _lock:
            _waiting -= 1
    return Lease() if got else None
