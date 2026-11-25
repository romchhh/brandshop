from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings

from shop.catalog_import import _photo_import_source_label
from shop.sync_schedule import next_sync_at, schedule_label


@override_settings(CELERY_TIMEZONE="Europe/Kyiv", CATALOG_SYNC_CRON_HOURS=(10, 18))
class SyncScheduleTests(SimpleTestCase):
    def test_next_is_same_day_morning(self):
        now = datetime(2026, 6, 12, 9, 15, tzinfo=ZoneInfo("Europe/Kyiv"))
        nxt = next_sync_at(now)
        self.assertEqual(nxt.hour, 10)
        self.assertEqual(nxt.day, 12)

    def test_next_is_evening_after_morning_slot(self):
        now = datetime(2026, 6, 12, 11, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
        nxt = next_sync_at(now)
        self.assertEqual((nxt.hour, nxt.day), (18, 12))

    def test_next_rolls_to_tomorrow(self):
        now = datetime(2026, 6, 12, 19, 0, tzinfo=ZoneInfo("Europe/Kyiv"))
        nxt = next_sync_at(now)
        self.assertEqual((nxt.hour, nxt.day), (10, 13))

    def test_schedule_label_mentions_both_hours(self):
        label = schedule_label()
        self.assertIn("10:00", label)
        self.assertIn("18:00", label)

    def test_photo_fingerprint_stable_and_short(self):
        a = _photo_import_source_label("https://drive.google.com/file/d/abc/view")
        b = _photo_import_source_label("https://drive.google.com/file/d/abc/view")
        c = _photo_import_source_label("https://drive.google.com/file/d/OTHER/view")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertLessEqual(len(a), 64)
        self.assertEqual(_photo_import_source_label("  "), "")
