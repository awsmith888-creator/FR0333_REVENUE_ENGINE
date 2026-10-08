"""FR-0333 development worker: durable SQLite receipts, deterministic clock ticks, no network calls."""
import argparse
import json
import os
import signal
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

CLOCKS = {"ONE_HOUR": 3600, "SIX_HOUR": 21600, "DAY": 86400}
SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 at_utc TEXT NOT NULL,
 kind TEXT NOT NULL,
 payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS blooms (
 event_id INTEGER PRIMARY KEY,
 state TEXT NOT NULL CHECK(state IN ('HOLD.BLOOM','FAILED.BLOOM','PROMOTED.BLOOM')),
 FOREIGN KEY(event_id) REFERENCES events(id)
);
"""

class Runtime:
    def __init__(self, db_path, clock=time.time):
        self.path = str(db_path)
        self.clock = clock
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def record(self, kind, payload, bloom=None):
        stamp = datetime.fromtimestamp(self.clock(), tz=timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute("INSERT INTO events(at_utc,kind,payload) VALUES (?,?,?)",
                                    (stamp, kind, json.dumps(payload, sort_keys=True)))
            if bloom:
                self.conn.execute("INSERT INTO blooms(event_id,state) VALUES (?,?)", (cur.lastrowid, bloom))
        return cur.lastrowid

    def tick(self):
        now = self.clock()
        clocks = {name: {"period_seconds": period, "elapsed_in_period": int(now) % period,
                         "remaining_seconds": period - (int(now) % period)}
                  for name, period in CLOCKS.items()}
        # These are software timebases, not evidence of external YouTube playback.
        return self.record("CLOCK.OBSERVATION", {"clocks": clocks, "lanes": 128, "supervisor": "MR.00"})

    def ingest_recovery(self, receipt):
        """Accept controller receipt; never promote a bloom automatically."""
        payload = {"source": receipt.source, "replacement": receipt.replacement,
                   "state": receipt.state.value, "reason": receipt.reason}
        return self.record("RECOVERY.RECEIPT", payload, bloom="HOLD.BLOOM")

    def count(self, kind=None):
        if kind is None:
            return self.conn.execute("SELECT count(*) FROM events").fetchone()[0]
        return self.conn.execute("SELECT count(*) FROM events WHERE kind=?", (kind,)).fetchone()[0]

    def close(self):
        self.conn.close()

def serve(db_path, interval=60, max_ticks=None):
    if interval <= 0:
        raise ValueError("interval must be positive")
    worker = Runtime(db_path)
    running = True
    def stop(_signum, _frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    ticks = 0
    try:
        worker.record("RUNTIME.START", {"mode": "development", "api_calls": False})
        while running and (max_ticks is None or ticks < max_ticks):
            worker.tick()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            # Wake regularly for responsive shutdown.
            until = time.monotonic() + interval
            while running and time.monotonic() < until:
                time.sleep(min(0.25, max(0, until - time.monotonic())))
    finally:
        worker.record("RUNTIME.STOP", {"ticks": ticks})
        worker.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("FR0333_DB", "data/fr0333_runtime.sqlite3"))
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--max-ticks", type=int, default=None)
    args = parser.parse_args()
    serve(args.db, args.interval, args.max_ticks)

if __name__ == "__main__":
    main()
