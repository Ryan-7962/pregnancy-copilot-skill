from datetime import date

from scripts.generate_weekly_review import default_week_range


def test_default_week_range_uses_recent_seven_days_ending_today():
    assert default_week_range(today=date(2026, 5, 6)) == ("2026-04-30", "2026-05-06")
