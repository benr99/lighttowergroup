import sys
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_schedule_policy import resolve_policy  # noqa: E402


class SchedulePolicyTests(unittest.TestCase):
    def test_summer_schedule_uses_nominal_cron_time(self) -> None:
        scheduled_day = date(2026, 7, 26)
        first = resolve_policy(
            event_name="schedule",
            trigger_cron="7 11 * * *",
            utc_date=scheduled_day,
        )
        second = resolve_policy(
            event_name="schedule",
            trigger_cron="7 12 * * *",
            utc_date=scheduled_day,
        )
        self.assertEqual(first["scheduled_local_time"], "07:07")
        self.assertEqual(first["skip"], "false")
        self.assertEqual(second["scheduled_local_time"], "08:07")
        self.assertEqual(second["skip"], "true")

    def test_winter_schedule_uses_the_other_utc_trigger(self) -> None:
        scheduled_day = date(2026, 1, 15)
        first = resolve_policy(
            event_name="schedule",
            trigger_cron="7 11 * * *",
            utc_date=scheduled_day,
        )
        second = resolve_policy(
            event_name="schedule",
            trigger_cron="7 12 * * *",
            utc_date=scheduled_day,
        )
        self.assertEqual(first["scheduled_local_time"], "06:07")
        self.assertEqual(first["skip"], "true")
        self.assertEqual(second["scheduled_local_time"], "07:07")
        self.assertEqual(second["skip"], "false")

    def test_manual_modes_are_explicit_and_never_skipped(self) -> None:
        for mode in ("shadow", "preview", "publish"):
            with self.subTest(mode=mode):
                policy = resolve_policy(
                    event_name="workflow_dispatch",
                    dispatch_mode=mode,
                )
                self.assertEqual(policy["skip"], "false")
                self.assertEqual(policy["mode"], mode)
                self.assertEqual(policy["scheduled_local_time"], "manual")

    def test_unknown_manual_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_policy(
                event_name="workflow_dispatch",
                dispatch_mode="unsafe",
            )


if __name__ == "__main__":
    unittest.main()
