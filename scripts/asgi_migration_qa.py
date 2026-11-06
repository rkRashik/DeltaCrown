"""Bounded, synthetic-only observations for the existing real-ASGI QA fixture."""
import io
import json
from pathlib import Path
import sys
import threading
import time


def migrate(folder, stage):
    from django.conf import settings
    from django.core.management import call_command
    from django.core.management.commands.migrate import Command
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    began = time.monotonic()
    owner = threading.get_ident()
    stopped = threading.Event()
    progress = {"events": [], "current": None, "last_completed": None, "completed_count": 0}

    def save(name, value):
        temporary = folder / (name + ".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(folder / (name + ".json"))

    def python_position():
        while not stopped.wait(.5):
            frame = sys._current_frames().get(owner)
            frames = []
            while frame is not None:
                frames.append(dict(file=Path(frame.f_code.co_filename).name,
                                   function=frame.f_code.co_name, line=frame.f_lineno))
                frame = frame.f_back
            save("migration_python", dict(elapsed_ms=round((time.monotonic() - began) * 1000, 2),
                                          frames=frames[:8]))  # No source, locals or exception text.

    sampler = threading.Thread(target=python_position, name="qa-migration-python", daemon=True)
    sampler.start()
    try:
        stage("migration_plan")
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        progress["plan"] = [f"{m.app_label}.{m.name}" for m, backwards in plan]
        progress["config"] = dict(planned=len(plan), applied=len(executor.loader.applied_migrations),
                                  backwards=sum(backwards for _, backwards in plan),
                                  disabled_modules=sum(v is None for v in settings.MIGRATION_MODULES.values()),
                                  conn_max_age=connection.settings_dict["CONN_MAX_AGE"])
        save("migration_progress", progress)
        stage("migration_plan", "completed")
        del executor

        class ObservedCommand(Command):
            def migration_progress_callback(self, action, migration=None, fake=False):
                now = time.monotonic()
                key = f"{migration.app_label}.{migration.name}" if migration else None
                item = dict(action=action, migration=key, elapsed_ms=round((now - began) * 1000, 2),
                            fake=fake)
                if action == "apply_start":
                    self.qa_started = now
                    progress["current"] = item
                elif action == "apply_success":
                    item["duration_ms"] = round((now - self.qa_started) * 1000, 2)
                    progress["last_completed"] = item
                    progress["completed_count"] += 1
                    progress["current"] = None
                if len(progress["events"]) < 1024:
                    progress["events"].append(item)
                save("migration_progress", progress)
                return super().migration_progress_callback(action, migration, fake)

        stage("migration_command")
        call_command(ObservedCommand(), interactive=False, verbosity=0, stdout=io.StringIO())
        stage("migration_command", "completed")
        progress["done"] = True
        save("migration_progress", progress)
    finally:
        stopped.set()
        sampler.join(timeout=1)


def poll(proc, folder, observer, startup_report, seconds=90):
    """Independent observer; scoped to this child's local QA sessions only."""
    began = time.monotonic()
    deadline = began + seconds
    printed = 0
    observations = []
    progress = {}
    python = {}

    def read(name, default):
        try:
            return json.loads((folder / (name + ".json")).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    while True:
        startup = startup_report()
        progress = read("migration_progress", progress)
        python = read("migration_python", python)
        events = progress.get("events", [])
        for item in events[printed:]:
            print("MIGRATION_PROGRESS " + json.dumps(item), flush=True)
        printed = len(events)
        with observer.cursor() as cursor:
            cursor.execute("SELECT state, wait_event_type, wait_event, "
                           "round(extract(epoch FROM (clock_timestamp()-state_change))*1000), "
                           "round(extract(epoch FROM (clock_timestamp()-query_start))*1000), "
                           "cardinality(pg_blocking_pids(pid)), "
                           "(SELECT count(*) FROM pg_locks l WHERE l.pid=a.pid AND NOT l.granted) "
                           "FROM pg_stat_activity a WHERE application_name=%s AND datname=%s",
                           ["ownlobby_asgi_qa_" + str(proc.pid), "ownlobby_test"])
            sessions = [dict(state=s, wait_type=t, wait=w,
                             state_age_ms=float(age) if age is not None else None,
                             query_age_ms=float(qage) if qage is not None else None,
                             blockers=blockers, ungranted_locks=locks)
                        for s, t, w, age, qage, blockers, locks in cursor.fetchall()]
        item = dict(elapsed_ms=round((time.monotonic() - began) * 1000, 2), sessions=sessions,
                    completed=progress.get("completed_count", 0), current=progress.get("current"),
                    python=python)
        if len(observations) < 200:
            observations.append(item)
        # Bounded metadata only; no SQL, database URLs, parameters or locals.
        print("MIGRATION_OBSERVER " + json.dumps(item), flush=True)
        status = proc.poll()
        if status is not None or time.monotonic() >= deadline or startup["child_error"]:
            summary = dict(startup=startup, config=progress.get("config"),
                           plan_first=progress.get("plan", [])[:3], plan_last=progress.get("plan", [])[-3:],
                           last_completed=progress.get("last_completed"), current=progress.get("current"),
                           completed_count=progress.get("completed_count", 0), observation=item,
                           observations=len(observations), child_exit_status=status)
            print("MIGRATION_QA_SUMMARY " + json.dumps(summary), flush=True)
            assert status == 0 and progress.get("done"), "Migration-only QA did not finish within 90 seconds"
            return summary
        time.sleep(min(1, max(0, deadline - time.monotonic())))
