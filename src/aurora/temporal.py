"""Shared monthly interval semantics for UI, analysis and dataset readers."""
import re
import numpy as np


def parse_month(value):
    text = str(value)
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])(?:-(0[1-9]|[12]\d|3[01]))?', text):
        raise ValueError('Expected YYYY-MM or a valid YYYY-MM-DD')
    # numpy validates the day before deliberately snapping to monthly resolution.
    return np.datetime64(text, 'D').astype('datetime64[M]')


def select_interval(dates, start, end):
    dates = np.asarray(dates).astype('datetime64[M]')
    start, end = parse_month(start), parse_month(end)
    if not len(dates) or np.isnat(dates).any() or np.any(np.diff(dates).astype(int) <= 0):
        raise ValueError('Calendar must be nonempty and strictly increasing')
    if start > end or start < dates[0] or end > dates[-1]:
        raise ValueError('Invalid interval or outside dataset availability')
    return (dates >= start) & (dates <= end)


def trend_eligibility(dates):
    dates = np.asarray(dates).astype('datetime64[M]')
    _, count = np.unique(dates.astype('datetime64[Y]'), return_counts=True)
    years = int((count >= 9).sum())
    return {'eligible': years >= 15, 'eligible_calendar_years': years,
            'minimum_years': 15, 'minimum_months_per_year': 9,
            'interpretation': 'trend eligibility still requires pixel-level coverage' if years >= 15
            else 'descriptive exploration only; insufficient long-term evidence'}


def quick_period(dates, years):
    dates = np.asarray(dates).astype('datetime64[M]')
    start = dates[-1]-np.timedelta64(years*12-1, 'M')
    if start < dates[0]:
        raise ValueError('Quick period exceeds available observations')
    return str(start), str(dates[-1])
