import sys
import os
sys.path.append(os.getcwd())

from app.services.scoring_engine import calculate_indicator_contribution


def test_higher_is_better_top_performer():
    """A student with a perfect score should contribute zero risk."""
    result = calculate_indicator_contribution(
        raw_value=100, weight=0.6, min_value=0, max_value=100, higher_is_better=True
    )
    assert result == 0.0


def test_higher_is_better_worst_performer():
    """A student scoring the minimum should contribute the full weighted risk."""
    result = calculate_indicator_contribution(
        raw_value=0, weight=0.6, min_value=0, max_value=100, higher_is_better=True
    )
    assert result == 60.0


def test_higher_is_better_mid_range():
    """A mid-range mark should produce a proportional contribution (matches real test case)."""
    result = calculate_indicator_contribution(
        raw_value=72.5, weight=0.6, min_value=0, max_value=100, higher_is_better=True
    )
    assert round(result, 2) == 16.5


def test_lower_is_better_worst_case():
    """For a 'risk factor' style indicator, a high raw value should contribute high risk."""
    result = calculate_indicator_contribution(
        raw_value=100, weight=0.5, min_value=0, max_value=100, higher_is_better=False
    )
    assert result == 50.0


def test_lower_is_better_best_case():
    """A 'risk factor' indicator at its minimum should contribute zero risk."""
    result = calculate_indicator_contribution(
        raw_value=0, weight=0.5, min_value=0, max_value=100, higher_is_better=False
    )
    assert result == 0.0


def test_zero_weight_produces_zero_contribution():
    """Edge case: a zero weight should always neutralize the contribution, regardless of value."""
    result = calculate_indicator_contribution(
        raw_value=0, weight=0.0, min_value=0, max_value=100, higher_is_better=True
    )
    assert result == 0.0


def test_determinism():
    """NFR-01: identical inputs must always produce identical outputs."""
    args = dict(raw_value=45.5, weight=0.35, min_value=0, max_value=100, higher_is_better=True)
    result1 = calculate_indicator_contribution(**args)
    result2 = calculate_indicator_contribution(**args)
    assert result1 == result2