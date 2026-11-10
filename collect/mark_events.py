#!/usr/bin/env python3
"""
collect/mark_events.py
Interactively mark event start/end times and log to CSV.

Usage:
    python collect/mark_events.py

Press Enter to mark START, then Enter to mark END.
Enter event type (breath / warm_hands / other).
Type 'q' at START prompt to quit.
"""

import sys
import csv
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config

EVENT_LOG = config.raw_dir / "new_events_log.csv"
EVENT_TYPES = ["breath", "warm_hands", "other"]

def get_next_event_id():
    """Return the next event ID by reading existing log."""
    if not EVENT_LOG.exists():
        return 1
    try:
        with EVENT_LOG.open("r", newline="") as f:
            reader = csv.DictReader(f)
            ids = [int(row["event_id"]) for row in reader if row.get("event_id", "").isdigit()]
            return max(ids) + 1 if ids else 1
    except Exception:
        return 1

def write_event(event_id, start_time, end_time, event_type):
    """Append one event row to the log CSV."""
    file_exists = EVENT_LOG.exists()
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["event_id", "start_time", "end_time", "event_type"])
        writer.writerow([event_id, start_time, end_time, event_type])

def main():
    print("=== Event Marker ===")
    print("Press Enter to mark START, then Enter to mark END.")
    print(f"Event types: {', '.join(EVENT_TYPES)}")
    print("Type 'q' at START prompt to quit.\n")

    event_id = get_next_event_id()
    print(f"Next event_id: {event_id}\n")

    try:
        while True:
            # ---- Step 1: Prompt for START ----
            start_prompt = input(f"Event {event_id} - Press Enter to mark START (or 'q' to quit): ")
            if start_prompt.strip().lower() == 'q':
                print("Quitting.")
                break

            start_time = datetime.now().isoformat(timespec="seconds")
            print(f"  START recorded: {start_time}")

            # ---- Step 2: Prompt for END ----
            end_prompt = input(f"Event {event_id} - Press Enter to mark END: ")
            end_time = datetime.now().isoformat(timespec="seconds")
            print(f"  END recorded: {end_time}")

            # ---- Step 3: Prompt for event type ----
            while True:
                event_type = input(f"Event type ({', '.join(EVENT_TYPES)}): ").strip().lower()
                if event_type in EVENT_TYPES:
                    break
                print(f"  Invalid. Choose from: {', '.join(EVENT_TYPES)}")

            # ---- Step 4: Write to CSV ----
            write_event(event_id, start_time, end_time, event_type)
            print(f"  Event {event_id} logged: {start_time} to {end_time} [{event_type}]\n")

            event_id += 1

    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()