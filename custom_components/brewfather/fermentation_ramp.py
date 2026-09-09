"""Continuous Brewfather fermentation-ramp adapter.

The selected upstream Brewfather integration exposes fermentation ramp lengths in
whole days but historically converts rising ramps into coarse 1 °C steps and does
not interpolate falling ramps. This adapter keeps the upstream coordinator
behavior intact, calculates a linear schedule target, and exposes that schedule as
read-only metadata for downstream consumers such as BrewAssistant.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .coordinator import BatchInfo, BrewfatherCoordinator, BrewfatherCoordinatorData


RAMP_METADATA_FIELDS = (
    "schedule_target_temperature",
    "schedule_ramp_active",
    "schedule_ramp_start_temperature",
    "schedule_ramp_target_temperature",
    "schedule_ramp_days",
    "schedule_ramp_started_at",
    "schedule_ramp_ends_at",
    "schedule_ramp_progress_percent",
)


class BrewfatherRampCoordinator(BrewfatherCoordinator):
    """Brewfather coordinator with continuous fermentation ramp targets."""

    @staticmethod
    def _interpolate_temperature(
        start_temperature: float,
        target_temperature: float,
        ramp_started_at: datetime,
        ramp_ends_at: datetime,
        now: datetime,
    ) -> float:
        """Return a clamped linear target for an active temperature ramp."""
        duration = (ramp_ends_at - ramp_started_at).total_seconds()
        if duration <= 0:
            return round(float(target_temperature), 1)
        elapsed = (now - ramp_started_at).total_seconds()
        progress = min(max(elapsed / duration, 0.0), 1.0)
        target = float(start_temperature) + (
            float(target_temperature) - float(start_temperature)
        ) * progress
        return round(target, 1)

    def get_batch_data(
        self,
        currentBatch: BatchInfo,
        currentTimeUtc: datetime,
    ) -> BrewfatherCoordinatorData | None:
        """Apply a continuous target while Brewfather says a ramp is active."""
        data = super().get_batch_data(currentBatch, currentTimeUtc)
        if data is None:
            return None

        recipe = currentBatch.batch.recipe
        fermentation = recipe.fermentation if recipe is not None else None
        steps = fermentation.steps if fermentation is not None else None
        if not steps:
            return data

        fermenting_start: int | None = None
        for note in currentBatch.batch.notes or []:
            if note.status == "Fermenting":
                fermenting_start = note.timestamp
        if fermenting_start is None:
            return data

        ordered_steps = sorted(
            (step for step in steps if step.actual_time is not None),
            key=lambda step: step.actual_time,
        )
        for index, step in enumerate(ordered_steps):
            if index == 0 or step.ramp is None or step.ramp <= 0:
                continue
            if step.step_temp is None:
                continue
            previous = ordered_steps[index - 1]
            if previous.step_temp is None:
                continue

            ramp_ends_at = self.datetime_fromtimestamp_with_fermentingstart(
                step.actual_time,
                fermenting_start,
            )
            ramp_started_at = ramp_ends_at - timedelta(days=float(step.ramp))
            if not ramp_started_at <= currentTimeUtc < ramp_ends_at:
                continue

            schedule_target = self._interpolate_temperature(
                previous.step_temp,
                step.step_temp,
                ramp_started_at,
                ramp_ends_at,
                currentTimeUtc,
            )
            progress = min(
                max(
                    (currentTimeUtc - ramp_started_at).total_seconds()
                    / max((ramp_ends_at - ramp_started_at).total_seconds(), 1.0),
                    0.0,
                ),
                1.0,
            )

            # Metadata is deliberately attached even when the upstream
            # "temperature ramping" option is disabled. Downstream consumers can
            # follow the schedule without forcing the upstream display behavior.
            data.schedule_target_temperature = schedule_target
            data.schedule_ramp_active = True
            data.schedule_ramp_start_temperature = float(previous.step_temp)
            data.schedule_ramp_target_temperature = float(step.step_temp)
            data.schedule_ramp_days = float(step.ramp)
            data.schedule_ramp_started_at = ramp_started_at
            data.schedule_ramp_ends_at = ramp_ends_at
            data.schedule_ramp_progress_percent = round(progress * 100.0, 1)

            if self.temperature_correction_enabled:
                data.current_step_temperature = schedule_target
            return data

        data.schedule_target_temperature = data.current_step_temperature
        data.schedule_ramp_active = False
        data.schedule_ramp_start_temperature = None
        data.schedule_ramp_target_temperature = None
        data.schedule_ramp_days = None
        data.schedule_ramp_started_at = None
        data.schedule_ramp_ends_at = None
        data.schedule_ramp_progress_percent = None
        return data


def install_ramp_sensor_metadata() -> None:
    """Expose schedule metadata on the existing Brewfather target sensor."""
    from .sensor import BrewfatherSensor, SensorKinds

    if getattr(BrewfatherSensor, "_continuous_ramp_metadata_installed", False):
        return

    original = BrewfatherSensor._refresh_sensor_data

    def _refresh_with_ramp_metadata(
        data: BrewfatherCoordinatorData,
        sensor_type: Any,
        device_class: Any,
        entity_id: str,
    ):
        result = original(data, sensor_type, device_class, entity_id)
        if data is not None and sensor_type == SensorKinds.fermenting_current_temperature:
            attrs = dict(result.extra_state_attributes or {})
            for field in RAMP_METADATA_FIELDS:
                attrs[field] = getattr(data, field, None)
            result.extra_state_attributes = attrs
        return result

    BrewfatherSensor._refresh_sensor_data = staticmethod(_refresh_with_ramp_metadata)
    BrewfatherSensor._continuous_ramp_metadata_installed = True
