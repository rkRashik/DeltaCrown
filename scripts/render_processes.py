"""Supervise web and one optional Celery worker inside the existing container.

No migrations, Beat, new service, or broker/queue changes. A child exiting tears
down the container so Render can restart it; it cannot stay silently web-only.
"""
import os
import signal
import subprocess
import sys
import time


def worker_command():
    return [sys.executable, '-m', 'celery', '-A', 'deltacrown', 'worker',
            '--pool=prefork', '--concurrency=1', '--prefetch-multiplier=1',
            '--queues=celery,default',
            '--without-gossip', '--without-mingle', '--without-heartbeat',
            '--loglevel=INFO', '--hostname=ownlobby@%h',
            '--soft-time-limit=120', '--time-limit=200',
            '--max-tasks-per-child=50', '--max-memory-per-child=150000']


def supervise(web_command, *, popen=subprocess.Popen, sleep=time.sleep):
    children = []

    def stop(signum=None, frame=None):
        for child in children:
            try:
                # Includes prefork children even if their parent already exited.
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        worker_env = dict(os.environ, DISABLE_INPROCESS_MATCH_REMINDER='1')
        children.append(popen(worker_command(), env=worker_env, start_new_session=True))
        children.append(popen(web_command, start_new_session=True))
        while all(child.poll() is None for child in children):
            sleep(0.5)
        return 1  # Even an unexpected clean child exit is an unhealthy container.
    finally:
        stop()
        deadline = time.monotonic() + 25
        for child in children:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('Supply the web command')
    raise SystemExit(supervise(sys.argv[1:]))
