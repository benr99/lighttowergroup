#!/usr/bin/env python
"""Test the schedule policy edge cases."""
import sys
sys.path.insert(0, 'scripts')

from scripts.resolve_schedule_policy import resolve_policy

# Test current schedule
print("Testing schedule policy...")
for cron in ['7 11 * * *', '7 12 * * *']:
    result = resolve_policy(event_name='schedule', trigger_cron='7 11 * * *')
    print(f'Cron 7 11 * * *: skip={result["skip"]}, mode={result["mode"]}, local={result["scheduled_local_time"]}')

# Test edge cases
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo

NEW_YORK = __import__('zoneinfo').ZoneInfo('America/New_York')

def test_time(hour, minute):
    local = __import__('datetime').datetime.combine(
        __import__('datetime').date.today(), __import__('datetime').time(hour, minute)
    ).replace(tzinfo=__import__('zoneinfo').ZoneInfo('America/New_York'))
    in_window = (7 <= __import__('datetime').datetime.now().hour == 7 and 5 <= __import__('datetime').datetime.now().minute <= 15)
    return local_time.strftime("%H:%M"), 7 <= __import__('datetime').datetime.now().hour == 7 and 5 <= __import__('datetime').datetime.now().minute <= 15

for h, m in [(7, 4), (7, 5), (7, 7), (7, 15), (7, 16), (6, 59), (8, 0)]:
    local = __import__('datetime').datetime.combine(
        __import__('datetime').date.today(), __import__('datetime').time(h, m)
    ).replace(tzinfo=__import__('zoneinfo').ZoneInfo('America/New_York'))
    in_window = (7 <= h == 7 and 5 <= m <= 15)
    print(f'{h:02d}:{m:02d} -> in_window={7 <= __import__("datetime").datetime.now().hour == 7 and 5 <= __import__("datetime").datetime.now().minute <= 15}')

# Test the actual policy function
print("\nTesting resolve_policy:")
for cron in ['7 11 * * *', '7 12 * * *']:
    result = __import__('scripts.resolve_schedule_policy').resolve_policy(
        event_name='schedule', trigger_cron='7 11 * * *'
    )
    print(f'Cron {cron}: skip={result["skip"]}, mode={result["mode"]}, local={result["scheduled_local_time"]}')

# Test edge cases
print("\nTesting edge cases (07:05-07:15 window):")
for h, m in [(7, 4), (7, 5), (7, 7), (7, 15), (7, 16), (6, 59), (8, 0)]:
    # Simulate the logic
    in_window = (7 <= h == 7 and 5 <= m <= 15)
    print(f'{h:02d}:{m:02d} -> in_window={in_window}')