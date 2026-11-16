import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aurora.temporal import parse_month, select_interval, trend_eligibility, quick_period


def test_monthly_inclusive_day_input():
    dates = np.arange('2001-01', '2026-01', dtype='datetime64[M]')
    assert select_interval(dates, '2020-02-29', '2020-04-30').sum() == 3
    assert parse_month('2020-02-29') == np.datetime64('2020-02')
    with pytest.raises(ValueError): parse_month('2019-02-29')
    with pytest.raises(ValueError): select_interval(dates, '2000-01', '2020-01')
    with pytest.raises(ValueError): select_interval(dates, '2020-01', '2019-01')


def test_quick_period_and_statistical_requirements():
    dates = np.arange('2001-01', '2026-01', dtype='datetime64[M]')
    assert quick_period(dates, 5) == ('2021-01', '2025-12')
    assert trend_eligibility(dates)['eligible']
    assert not trend_eligibility(dates[-60:])['eligible']
    # 15 calendar year labels with only six months each is still insufficient.
    assert not trend_eligibility(dates[np.arange(len(dates)) % 12 < 6])['eligible']
    with pytest.raises(ValueError): quick_period(dates[-24:], 5)
