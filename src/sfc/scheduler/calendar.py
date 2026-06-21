"""Calendar utilities — cron expression parsing and next-run calculation."""

from __future__ import annotations

import math
from datetime import datetime, timedelta


class CronExpression:
    """Minimal cron expression parser.

    Supports: M H dom mon dow  (5 fields, space-separated)
    Supports: *, */N, single values, comma-lists, ranges (a-b)
    Examples:
        "0 7 * * *"    — daily at 07:00
        "0 9 * * 1"    — every Monday at 09:00
        "0 0 1 * *"    — first of each month at midnight
        "*/30 * * * *" — every 30 minutes
        "0 8,18 * * *" — at 08:00 and 18:00 daily
    """

    def __init__(self, expression: str) -> None:
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression (need 5 fields): {expression!r}")
        self.minute_expr = parts[0]
        self.hour_expr = parts[1]
        self.dom_expr = parts[2]
        self.month_expr = parts[3]
        self.dow_expr = parts[4]

    @staticmethod
    def _parse_field(expr: str, min_val: int, max_val: int) -> set[int]:
        result: set[int] = set()
        for part in expr.split(","):
            if part == "*":
                result.update(range(min_val, max_val + 1))
            elif part.startswith("*/"):
                step = int(part[2:])
                result.update(range(min_val, max_val + 1, step))
            elif "-" in part:
                a, b = part.split("-", 1)
                result.update(range(int(a), int(b) + 1))
            else:
                result.add(int(part))
        return result

    def _valid_minutes(self) -> set[int]:
        return self._parse_field(self.minute_expr, 0, 59)

    def _valid_hours(self) -> set[int]:
        return self._parse_field(self.hour_expr, 0, 23)

    def _valid_doms(self) -> set[int]:
        return self._parse_field(self.dom_expr, 1, 31)

    def _valid_months(self) -> set[int]:
        return self._parse_field(self.month_expr, 1, 12)

    def _valid_dows(self) -> set[int]:
        # 0=Sunday, 1=Monday, ..., 6=Saturday
        return self._parse_field(self.dow_expr, 0, 6)

    def matches(self, dt: datetime) -> bool:
        """Return True if the given datetime matches this cron expression."""
        python_dow = dt.isoweekday() % 7  # Monday=1 → 1, Sunday=0
        return (
            dt.minute in self._valid_minutes()
            and dt.hour in self._valid_hours()
            and dt.day in self._valid_doms()
            and dt.month in self._valid_months()
            and python_dow in self._valid_dows()
        )

    def next_run(self, after: datetime | None = None) -> datetime:
        """Return the next datetime (minute precision) after `after`."""
        dt = (after or datetime.utcnow()).replace(second=0, microsecond=0)
        dt += timedelta(minutes=1)
        # Scan forward up to 1 year
        for _ in range(525_600):  # max minutes in a year
            if self.matches(dt):
                return dt
            dt += timedelta(minutes=1)
        raise RuntimeError("Could not find next run time within one year")


class CycleCalendar:
    """Utility to calculate schedule times for operating cycles."""

    @staticmethod
    def next_daily(hour: int = 7, minute: int = 0) -> datetime:
        now = datetime.utcnow()
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    @staticmethod
    def next_weekly(weekday: int = 0, hour: int = 9, minute: int = 0) -> datetime:
        """weekday: 0=Monday, 6=Sunday"""
        now = datetime.utcnow()
        days_ahead = weekday - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.hour >= hour):
            days_ahead += 7
        target = (now + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return target

    @staticmethod
    def next_monthly(day: int = 1, hour: int = 8, minute: int = 0) -> datetime:
        now = datetime.utcnow()
        candidate = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            # Move to next month
            if now.month == 12:
                candidate = candidate.replace(year=now.year + 1, month=1)
            else:
                candidate = candidate.replace(month=now.month + 1)
        return candidate

    @staticmethod
    def next_quarterly(hour: int = 8) -> datetime:
        now = datetime.utcnow()
        quarter_starts = [1, 4, 7, 10]
        for month in quarter_starts:
            candidate = now.replace(
                month=month, day=1, hour=hour, minute=0, second=0, microsecond=0
            )
            if candidate > now:
                return candidate
        # Next year Q1
        return now.replace(year=now.year + 1, month=1, day=1, hour=hour, minute=0, second=0, microsecond=0)

    @staticmethod
    def next_annual(month: int = 1, day: int = 1, hour: int = 9) -> datetime:
        now = datetime.utcnow()
        candidate = now.replace(
            month=month, day=day, hour=hour, minute=0, second=0, microsecond=0
        )
        if candidate <= now:
            candidate = candidate.replace(year=now.year + 1)
        return candidate

    @staticmethod
    def seconds_until(target: datetime) -> float:
        delta = (target - datetime.utcnow()).total_seconds()
        return max(0.0, delta)
