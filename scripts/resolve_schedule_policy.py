"""Resolve whether a curated Insights workflow trigger should run.

GitHub Actions cron jobs can begin well after their nominal trigger time.  The
decision therefore uses the cron expression that fired the workflow, not the
runner's wall clock.  Two UTC schedules are registered so that exactly one maps
to 07:07 in New York through both daylight-saving offsets.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")
MANUAL_MODES = {"shadow", "preview", "publish"}


def resolve_policy(
    *,
    event_name: str,
    trigger_cron: str = "",
    dispatch_mode: str = "shadow",
    utc_date: date | None = None,
) -> dict[str, str]:
    """Return GitHub-output-friendly execution policy values."""
    if event_name != "schedule":
        mode = dispatch_mode or "shadow"
        if mode not in MANUAL_MODES:
            raise ValueError(f"Unsupported manual run mode: {mode}")
        return {
            "skip": "false",
            "mode": mode,
            "scheduled_local_time": "manual",
        }

    fields = trigger_cron.split()
    if len(fields) != 5:
        raise ValueError(f"Invalid schedule expression: {trigger_cron!r}")
    try:
        minute = int(fields[0])
        hour = int(fields[1])
    except ValueError as exc:
        raise ValueError(
            f"Schedule minute and hour must be integers: {trigger_cron!r}"
        ) from exc
    if not 0 <= minute <= 59 or not 0 <= hour <= 23:
        raise ValueError(f"Schedule time is out of range: {trigger_cron!r}")

    scheduled_date = utc_date or datetime.now(timezone.utc).date()
    planned_utc = datetime.combine(
        scheduled_date,
        time(hour=hour, minute=minute),
        tzinfo=timezone.utc,
    )
    local_time = planned_utc.astimezone(NEW_YORK)
    local_hour = local_time.hour
    local_minute = local_time.minute
    # Accept runs between 07:05 and 07:15 NY time (cron fires at 07:07 but may be delayed)
    in_window = local_hour == 7 and 5 <= local_minute <= 15
    local_time_str = local_time.strftime("%H:%M")
    return {
        "skip": "false" if in_window else "true",
        "mode": "publish",
        "scheduled_local_time": local_time_str,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--trigger-cron", default="")
    parser.add_argument("--dispatch-mode", default="shadow")
    args = parser.parse_args()

    policy = resolve_policy(
        event_name=args.event_name,
        trigger_cron=args.trigger_cron,
        dispatch_mode=args.dispatch_mode,
    )
    for key, value in policy.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
