"""Focused tests for continuous Brewfather fermentation ramps."""

from datetime import datetime, timedelta, timezone

from custom_components.brewfather.fermentation_ramp import BrewfatherRampCoordinator


def test_interpolate_rising_ramp_midpoint():
    start = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)

    assert BrewfatherRampCoordinator._interpolate_temperature(
        18.0,
        20.5,
        start,
        end,
        start + timedelta(hours=12),
    ) == 19.2


def test_interpolate_falling_ramp_midpoint():
    start = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)

    assert BrewfatherRampCoordinator._interpolate_temperature(
        20.0,
        2.0,
        start,
        end,
        start + timedelta(hours=12),
    ) == 11.0


def test_interpolate_clamps_before_and_after_ramp():
    start = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)

    assert BrewfatherRampCoordinator._interpolate_temperature(
        18.0,
        20.5,
        start,
        end,
        start - timedelta(hours=1),
    ) == 18.0
    assert BrewfatherRampCoordinator._interpolate_temperature(
        18.0,
        20.5,
        start,
        end,
        end + timedelta(hours=1),
    ) == 20.5
