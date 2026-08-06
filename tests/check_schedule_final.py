#!/usr/bin/env python
"""Test schedule policy edge cases."""
import sys
sys.path.insert(0, 'scripts')

from scripts.resolve_schedule_policy import resolve_policy
from datetime import datetime, time
from zoneinfo import ZoneInfo

# Test current schedule
print("Testing current schedule...")
for cron in ['7 11 * * *', '7 12 * * *']:
    result = resolve_policy(event_name='schedule', trigger_cron='7 11 * * *')
    print(f'Cron 7 11 * * *: skip={result["skip"]}, mode={result["mode"]}, local={result["scheduled_local_time"]}')

# Test edge cases
print("\nTesting edge cases (07:05-07:15 window):")
for h, m in [(7, 4), (7, 5), (7, 7), (7, 15), (7, 16), (6, 59), (8, 0)]:
    local = datetime.combine(
        __import__('datetime').date.today(), time(h, m)
    ).replace(tzinfo=__import__('zoneinfo').ZoneInfo('America/New_York'))
    in_window = (7 <= h == 7 and 5 <= m <= 15)  # Fixed logic
    print(f'{h:02d}:{m:02d} -> in_window={5 <= m <= 15}')  # Fixed logic

# Test the actual policy function
print("\nTesting resolve_policy:")
for cron in ['7 11 * * *', '7 12 * * *']:
    result = resolve_policy(event_name='schedule', trigger_cron='7 11 * * *')
    print(f'Cron {cron}: skip={result["skip"]}, mode={result["mode"]}, local={result["scheduled_local_time"]}')

# Test edge cases
print("\nTesting edge cases (07:05-07:15 window):")
for h, m in [(7, 4), (7, 5), (7, 7), (7, 15), (7, 16), (6, 59), (8, 0)]:
    h_val = h
    m_val = m
    in_window = (7 <= h_val == 7 and 5 <= m_val <= 15)
    print(f'{h:02d}:{m:02d} -> in_window={in_window}')