"""Verify the day boundary, recovery, and upload guard use one timetable."""
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

os.environ["DISABLE_BACKGROUND_THREADS"] = "1"
os.environ.setdefault("AUTOMATION_DATA_DIR", tempfile.mkdtemp())
from app import channels, main
from app.upload_ledger import UploadLedger


EXPECTED_HOURS = {
    "default": (10, 18),
    "goplustrader": (11, 19),
    "channel3": (6, 14),
    "pockettrade": (12, 20),
    "zingtrader": (13, 21),
}


class StaggeredScheduleTests(unittest.TestCase):
    def test_ten_distinct_slots_prepared_on_previous_evening(self):
        now = datetime(2026, 10, 20, 22, tzinfo=main.IST)
        all_slots = []
        for channel, hours in EXPECTED_HOURS.items():
            slots = main.get_required_scheduler_slots(now, channel)
            self.assertEqual([s.hour for s in slots], list(hours))
            self.assertTrue(all(s.date() == date(2026, 10, 21) for s in slots))
            all_slots.extend(slots)
        self.assertEqual(len(set(all_slots)), 10)
        ordered = sorted(all_slots)
        self.assertTrue(all(b - a >= timedelta(hours=1)
                            for a, b in zip(ordered, ordered[1:])))

    def test_transition_day_does_not_add_new_afternoon_slots(self):
        now = datetime(2026, 10, 20, 13, 30, tzinfo=main.IST)
        for channel in channels.CHANNELS:
            expected = [] if channel == "channel3" else [18]
            slots = main.get_required_scheduler_slots(now, channel)
            self.assertEqual([s.hour for s in slots], expected)

    def test_recovery_keeps_only_future_slots_after_cutover(self):
        now = datetime(2026, 10, 21, 13, 30, tzinfo=main.IST)
        for channel, hours in EXPECTED_HOURS.items():
            self.assertEqual(
                [s.hour for s in main.get_required_scheduler_slots(now, channel)],
                [hours[1]])
        # The existing five-minute lead guard still applies at a new slot.
        near = datetime(2026, 10, 21, 20, 56, tzinfo=main.IST)
        self.assertEqual(main.get_required_scheduler_slots(near, "zingtrader"), [])

    def test_upload_guard_accepts_new_slots_in_utc_and_rejects_old_slots(self):
        for channel, hours in EXPECTED_HOURS.items():
            with self.subTest(channel=channel), tempfile.TemporaryDirectory() as directory:
                video = Path(directory, "video.mp4")
                video.write_bytes(channel.encode())
                ledger = UploadLedger(str(Path(directory, "ledger.json")))
                slot = datetime(2026, 10, 21, hours[0], tzinfo=main.IST)
                self.assertIsNone(ledger.begin(
                    channel, slot.astimezone(timezone.utc), str(video)))
                for hour, minute in channels.PREVIOUS_TIMES[channel]:
                    if (hour, minute) not in channels.CHANNELS[channel]["times"]:
                        with self.assertRaises(ValueError):
                            ledger.begin(channel, slot.replace(hour=hour, minute=minute),
                                         str(video))

    def test_status_distinguishes_today_from_new_timetable(self):
        now = datetime(2026, 10, 20, 13, 30, tzinfo=main.IST)
        with patch.object(main, "now_ist", return_value=now), \
                patch.object(main, "load_buffer", return_value={"slots": []}), \
                patch.object(main, "load_automation_state", return_value={"enabled": True}):
            status = main.app.test_client().get("/").get_json()
        self.assertEqual(status["schedule_effective_date"], "2026-10-21")
        self.assertEqual(status["channels"]["zingtrader"]["publish_times"],
                         ["13:00 IST", "21:00 IST"])
        self.assertEqual(status["channels"]["zingtrader"]["today_publish_times"],
                         ["10:00 IST", "18:00 IST"])


if __name__ == "__main__":
    unittest.main()
