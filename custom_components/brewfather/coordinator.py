from __future__ import annotations
import logging
from logging import DEBUG
from copy import copy
from datetime import datetime, timezone, timedelta
import math
from typing import Optional, Any
from .connection import Connection
from .models.batches_item import BatchesItemElement
from .models.batch_item import (
    Fermentation,
    BatchItem,
    Step,
    Reading,
    Event
)
from .models.custom_stream_data import custom_stream_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature, STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN,
    MS_IN_DAY,
    CONF_RAMP_TEMP_CORRECTION,
    CONF_MULTI_BATCH,
    CONF_ALL_BATCH_INFO_SENSOR,
    CONF_CUSTOM_STREAM_ENABLED,
    CONF_CUSTOM_STREAM_LOGGING_ID,
    CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME,
    CONF_CUSTOM_STREAM_DEVICE_NAME,
    CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME,
    CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME,
    CONF_CUSTOM_STREAM_DEVICE_SOURCE,
    CONF_CUSTOM_STREAM_REPORT_SOURCE,
    DEFAULT_CUSTOM_STREAM_DEVICE_NAME,
    DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE,
    DEFAULT_CUSTOM_STREAM_REPORT_SOURCE,
    CUSTOM_STREAM_MIN_INTERVAL_SECONDS,
    CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

def sort_by_actual_time(entity: Fermentation):
    return entity.actual_time

class BrewfatherCoordinatorData:
    batch_id: Optional[str]
    brew_name: Optional[str]
    current_step_temperature: Optional[float]
    next_step_date: Optional[datetime.datetime]
    next_step_temperature: Optional[float]
    last_reading: Optional[Reading]
    other_batches: list[BrewfatherCoordinatorData]
    all_batches_data: Optional[list[BatchItem]]
    start_date: Optional[datetime.datetime]
    batch_notes: Optional[str]
    events: Optional[list[Event]]
    brew_tracker: Optional[dict[str, Any]]
    brew_tracker_batch_id: Optional[str]
    brew_tracker_batch_name: Optional[str]
    brew_tracker_recipe_name: Optional[str]
    brew_tracker_batch_status: Optional[str]
    brew_tracker_recipe: Optional[dict[str, Any]]

    def __init__(self):
        # set defaults to None
        self.batch_id = None
        self.brew_name = None
        self.current_step_temperature = None
        self.next_step_date = None
        self.next_step_temperature = None
        self.last_reading = None
        self.other_batches = []
        self.all_batches_data = None
        self.start_date = None
        self.batch_notes = None
        self.events = None
        self.brew_tracker = None
        self.brew_tracker_batch_id = None
        self.brew_tracker_batch_name = None
        self.brew_tracker_recipe_name = None
        self.brew_tracker_batch_status = None
        self.brew_tracker_recipe = None


class BatchInfo:
    batch: BatchItem
    #readings: list[Reading]
    last_reading: Reading
    brew_tracker: dict[str, Any] | None
    
    #def __init__(self, batch: BatchItem, readings: list[Reading]):
    def __init__(self, batch: BatchItem, last_reading: Reading, brew_tracker: dict[str, Any] | None):
        self.batch = batch
        self.last_reading = last_reading
        self.brew_tracker = brew_tracker

class BrewfatherCoordinator(DataUpdateCoordinator[BrewfatherCoordinatorData]):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry, update_interval: timedelta):
        self.multi_batch_mode = entry.data.get(CONF_MULTI_BATCH, False)
        self.all_batch_info_sensor = entry.data.get(CONF_ALL_BATCH_INFO_SENSOR, False)
        self.temperature_correction_enabled = entry.data.get(CONF_RAMP_TEMP_CORRECTION, False)
        self.connection = Connection(
            entry.data.get(CONF_USERNAME), 
            entry.data.get(CONF_PASSWORD)
        )
        self.custom_stream_enabled = entry.data.get(CONF_CUSTOM_STREAM_ENABLED, False)
        self.last_update_success_time: Optional[datetime] = None
        self.custom_stream_last_post_time: Optional[datetime] = None
        self.custom_stream_last_attempt_time: Optional[datetime] = None
        self.custom_stream_last_success_time: Optional[datetime] = None
        self.custom_stream_last_eligible_sample_time: Optional[datetime] = None
        self.custom_stream_last_result: str = (
            "idle" if self.custom_stream_enabled else "disabled"
        )
        self.custom_stream_last_reason: Optional[str] = None
        self.custom_stream_last_payload_fields: list[str] = []
        if self.custom_stream_enabled:
            self.custom_stream_logging_id = entry.data.get(CONF_CUSTOM_STREAM_LOGGING_ID, None)
            self.custom_stream_device_name = entry.data.get(
                CONF_CUSTOM_STREAM_DEVICE_NAME,
                DEFAULT_CUSTOM_STREAM_DEVICE_NAME,
            )
            self.custom_stream_temperature_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME,
                None,
            )
            self.custom_stream_gravity_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME,
                None,
            )
            self.custom_stream_aux_temperature_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME,
                None,
            )
            self.custom_stream_ext_temperature_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME,
                None,
            )
            self.custom_stream_temp_target_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME,
                None,
            )
            self.custom_stream_gravity_target_entity_name = entry.data.get(
                CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME,
                None,
            )
            self.custom_stream_device_source = entry.data.get(
                CONF_CUSTOM_STREAM_DEVICE_SOURCE,
                DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE,
            )
            self.custom_stream_report_source = entry.data.get(
                CONF_CUSTOM_STREAM_REPORT_SOURCE,
                DEFAULT_CUSTOM_STREAM_REPORT_SOURCE,
            )

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> BrewfatherCoordinatorData:
        """Update data via library."""
        try:
            _LOGGER.debug("Updating data via library")
            data = await self.update()
            # Update the last successful update time
            self.last_update_success_time = datetime.now(timezone.utc)
            return data
        except Exception as ex:
            _LOGGER.error("Error updating Brewfather data: %s", str(ex))
            raise UpdateFailed(f"Error communicating with Brewfather API: {ex}") from ex

    async def update(self) -> BrewfatherCoordinatorData:
        _LOGGER.debug("Updating data...")
        allBatches = await self.connection.get_batches()

        fermentingBatches:list[BatchInfo] = []
        all_batches_data:list[BatchInfo] = []

        # Custom Stream is deliberately decoupled from arbitrary coordinator refreshes.
        # Brewfather documents a maximum of one POST per 15 minutes per device
        # name. Device readings are batch-eligible while the batch is Fermenting
        # or Conditioning. The outbound logger remains best-effort and may never
        # make the normal Brewfather read path unavailable.
        if self.custom_stream_enabled:
            stream_now = datetime.now(timezone.utc)
            if not self._custom_stream_due(stream_now):
                self.custom_stream_last_result = "throttled"
                self.custom_stream_last_reason = "local 15-minute device rate limit"
            elif not await self._custom_stream_batch_active(allBatches):
                self.custom_stream_last_result = "inactive_batch"
                self.custom_stream_last_reason = (
                    "no Brewfather batch in Fermenting or Conditioning"
                )
            else:
                stream_data = self.create_custom_stream_data(now=stream_now)
                if stream_data is None:
                    self.custom_stream_last_result = "not_eligible"
                    if self.custom_stream_last_reason is None:
                        self.custom_stream_last_reason = (
                            "no fresh eligible primary temperature"
                        )
                    _LOGGER.debug(
                        "No eligible data was found to post to custom stream: %s",
                        self.custom_stream_last_reason,
                    )
                else:
                    self.custom_stream_last_eligible_sample_time = stream_now
                    self.custom_stream_last_attempt_time = stream_now
                    payload = self.connection.to_dict(stream_data)
                    self.custom_stream_last_payload_fields = sorted(payload)
                    _LOGGER.debug(
                        "Posting Brewfather custom stream data for device %s",
                        stream_data.name,
                    )
                    try:
                        success = await self.connection.post_custom_stream(
                            self.custom_stream_logging_id,
                            stream_data,
                        )
                        if success:
                            self.custom_stream_last_post_time = stream_now
                            self.custom_stream_last_success_time = stream_now
                            self.custom_stream_last_result = "sent"
                            self.custom_stream_last_reason = "Brewfather returned success"
                        else:
                            self.custom_stream_last_result = "rejected"
                            self.custom_stream_last_reason = (
                                "Brewfather response did not confirm success"
                            )
                            _LOGGER.error("Failed to post custom stream data")
                    except Exception as ex:
                        self.custom_stream_last_result = "error"
                        self.custom_stream_last_reason = str(ex)
                        _LOGGER.warning(
                            "Custom stream POST failed; continuing normal update: %s",
                            ex,
                        )

        for batch in allBatches:
            batchData = await self.connection.get_batch(batch.id)
            last_reading = await self.connection.get_last_reading(batch.id)
            brew_tracker = await self.connection.get_brewtracker(batch.id)
            fermentingBatches.append(BatchInfo(batchData, last_reading, brew_tracker))

            if self.all_batch_info_sensor:
                readings = await self.connection.get_readings(batch.id)
                all_batch_data = copy(batchData)
                all_batch_data.readings = readings

                all_batches_data.append(all_batch_data)
            elif not self.multi_batch_mode:
                break
        
        currentTimeUtc = datetime.now().astimezone()
        main_batch_data: BrewfatherCoordinatorData = None
        #batch_data:list[BrewfatherCoordinatorData] = []
        for fermenting_batch in fermentingBatches:
            batch_data = self.get_batch_data(fermenting_batch, currentTimeUtc)

            if batch_data is None:
                continue
            
            if main_batch_data is None:
                main_batch_data = batch_data
            else:
                if self.multi_batch_mode:
                    main_batch_data.other_batches.append(batch_data)
                else:
                    break

        if main_batch_data is None:
            main_batch_data = BrewfatherCoordinatorData()
        
        if self.all_batch_info_sensor:
            main_batch_data.all_batches_data = all_batches_data

        await self.add_brewtracker_discovery_data(main_batch_data, allBatches)
            
        return main_batch_data

    async def add_brewtracker_recipe_data(self, data: BrewfatherCoordinatorData) -> None:
        """Attach the complete recipe for the active BrewTracker batch when available.

        Recipe enrichment is intentionally best-effort. A temporary failure while
        loading the full batch must not make the existing BrewTracker runtime feed
        unavailable.
        """
        batch_id = data.brew_tracker_batch_id or data.batch_id
        if batch_id is None:
            return

        try:
            raw_batch = await self.connection.get_batch_raw(batch_id)
        except Exception as ex:
            _LOGGER.warning(
                "Unable to load full BrewTracker recipe for batch %s: %s",
                batch_id,
                ex,
            )
            return

        if not isinstance(raw_batch, dict):
            return

        recipe = raw_batch.get("recipe")
        if not isinstance(recipe, dict):
            return

        data.brew_tracker_recipe = recipe
        if data.brew_tracker_recipe_name is None:
            recipe_name = recipe.get("name")
            if isinstance(recipe_name, str):
                data.brew_tracker_recipe_name = recipe_name
        if data.brew_name is None:
            data.brew_name = data.brew_tracker_recipe_name
        if data.brew_tracker_batch_name is None:
            batch_name = raw_batch.get("name")
            if isinstance(batch_name, str):
                data.brew_tracker_batch_name = batch_name
        if data.brew_tracker_batch_status is None:
            batch_status = raw_batch.get("status")
            if isinstance(batch_status, str):
                data.brew_tracker_batch_status = batch_status

    async def add_brewtracker_discovery_data(
        self,
        data: BrewfatherCoordinatorData,
        fermenting_batches: list[BatchesItemElement],
    ) -> None:
        """Find an active Brew Tracker even when no batch is currently fermenting."""
        if self._brewtracker_active(data.brew_tracker):
            data.brew_tracker_batch_id = data.batch_id
            data.brew_tracker_recipe_name = data.brew_name
            await self.add_brewtracker_recipe_data(data)
            return

        checked_batch_ids = {batch.id for batch in fermenting_batches if batch.id is not None}
        all_batches = await self.connection.get_all_batches()

        for batch in all_batches:
            if batch.id is None or batch.id in checked_batch_ids:
                continue

            brew_tracker = await self.connection.get_brewtracker(batch.id)
            if not self._brewtracker_active(brew_tracker):
                continue

            data.brew_tracker = brew_tracker
            data.brew_tracker_batch_id = batch.id
            data.brew_tracker_batch_name = batch.name
            data.brew_tracker_recipe_name = batch.recipe.name if batch.recipe is not None else None
            data.brew_tracker_batch_status = batch.status

            if data.batch_id is None:
                data.batch_id = batch.id
            if data.brew_name is None and batch.recipe is not None:
                data.brew_name = batch.recipe.name

            await self.add_brewtracker_recipe_data(data)

            _LOGGER.debug(
                "Active Brew Tracker found on batch %s (%s)",
                data.brew_tracker_batch_id,
                data.brew_tracker_recipe_name,
            )
            return

    @staticmethod
    def _brewtracker_active(brew_tracker: dict[str, Any] | None) -> bool:
        if not isinstance(brew_tracker, dict):
            return False
        return brew_tracker.get("enabled") is True and len(brew_tracker.get("stages") or []) > 0
    
    def get_batch_data(self, currentBatch: BatchInfo, currentTimeUtc: datetime) -> BrewfatherCoordinatorData | None:
        fermenting_start: int | None = None
        if currentBatch.batch.notes is not None:
            for note in currentBatch.batch.notes:
                if note.status == "Fermenting":
                    fermenting_start = note.timestamp
        
        if fermenting_start is None:
            return None
        
        currentStep: Step | None = None
        nextStep: Step | None = None
        prevStep: Step | None = None
        curren_step_is_ramping = False
        current_step_actual_start_time_utc: datetime|None

        if currentBatch.batch.recipe is not None and currentBatch.batch.recipe.fermentation is not None and currentBatch.batch.recipe.fermentation.steps is not None:
            _LOGGER.debug("%s (%s) | CurrentTimeUtc: %s", currentBatch.batch.recipe.name, currentBatch.batch.id, currentTimeUtc.strftime("%m/%d/%Y, %H:%M:%S"))
            _LOGGER.debug("-------------------------------------- Fermentation steps -------- (tce:\t%s)---------------------------------------------", self.temperature_correction_enabled)
            for (index, step) in enumerate[Step](
                sorted(currentBatch.batch.recipe.fermentation.steps, key=lambda x: x.actual_time)
            ):
                step_start_datetime_utc = self.datetime_fromtimestamp_with_fermentingstart(
                    step.actual_time, fermenting_start
                )
                step_end_datetime_utc = self.datetime_fromtimestamp_with_fermentingstart(
                    step.actual_time + step.step_time * MS_IN_DAY, fermenting_start
                )

                actual_start_time_utc = step_start_datetime_utc
                if self.temperature_correction_enabled and step.ramp is not None and step.ramp > 0:
                    actual_start_time_utc = step_start_datetime_utc + timedelta(days = -1 * step.ramp)

                _LOGGER.debug("| %s\tstarts: %s\tends: %s\tramp: %s\tactualstart: %s |", step.step_temp, step_start_datetime_utc.strftime("%m/%d/%Y, %H:%M:%S"), step_end_datetime_utc.strftime("%m/%d/%Y, %H:%M:%S"), step.ramp, actual_start_time_utc.strftime("%m/%d/%Y, %H:%M:%S"))

                # check if start date is in past, we will keep looping so the latest step that matches will be current step.
                # this way it will also work for steps with ramping even if we have temperature_correction_enabled is disabled
                if actual_start_time_utc <= currentTimeUtc:
                    currentStep = step
                    current_step_actual_start_time_utc = actual_start_time_utc
                    if step_start_datetime_utc > currentTimeUtc:
                        curren_step_is_ramping = True
                    if index > 0:
                        prevStep = currentBatch.batch.recipe.fermentation.steps[index - 1]
                # check if start date is in future
                elif actual_start_time_utc > currentTimeUtc:
                    nextStep = step
                    break

        _LOGGER.debug("-----------------------------------------------------------------------------------------------------------------------------")

        data = BrewfatherCoordinatorData()
        data.batch_id = currentBatch.batch.id
        data.brew_name = currentBatch.batch.recipe.name
        data.last_reading = currentBatch.last_reading
        data.start_date = self.datetime_fromtimestamp(fermenting_start)
        data.batch_notes = currentBatch.batch.batch_notes
        data.events = currentBatch.batch.events
        data.brew_tracker = currentBatch.brew_tracker
        data.brew_tracker_batch_id = currentBatch.batch.id
        data.brew_tracker_batch_name = currentBatch.batch.name
        data.brew_tracker_recipe_name = currentBatch.batch.recipe.name if currentBatch.batch.recipe is not None else None
        data.brew_tracker_batch_status = currentBatch.batch.status

        # if currentBatch.readings is not None and len(currentBatch.readings) > 0:
        #     data.last_reading = sorted(currentBatch.readings, key=lambda r: r.time, reverse=True)[0]

        if currentStep is not None:
            data.current_step_temperature = currentStep.step_temp
            _LOGGER.debug("Current step: %s, ramp days: %s", currentStep.step_temp, currentStep.ramp)

            rampingStep = currentStep
            stepBeforeRamp = prevStep
            if self.temperature_correction_enabled and curren_step_is_ramping and stepBeforeRamp is not None and rampingStep.ramp is not None and rampingStep.ramp > 0:
                #instead of calculating what the temperature increase should be every hour we have to calculate how often we have to increase of decrease 1 whole degree C
                _LOGGER.debug("Next temperature has a ramp value of %s days", rampingStep.ramp)
                
                #from 20 to 25 in 24 hours
                #5 steps in 24 hour
                #24 / 5  = 4.8 hour 
                #each step will last 4.8 hours
                #step       temp        increase    new temp    start time, hours
                #0          20          0           20          0
                #1          20          1           21          4.8
                #2          20          2           22          9.6
                #3          20          3           23          14.4
                #4          20          4           24          19.2
                #end        25          0           0           24 (or 0 since the new step has started)

                number_of_steps = math.floor(rampingStep.step_temp - stepBeforeRamp.step_temp)
                if number_of_steps > 0:
                    ramp_hours = rampingStep.ramp * 24
                    hours_per_ramp = ramp_hours / number_of_steps

                    if _LOGGER.isEnabledFor(DEBUG):
                        _LOGGER.debug("------------------------------ Ramping schedule ----------------------------")
                        _LOGGER.debug("| Step\tTemp\tIncrease\tNew temp\tStart time (hours delta) |")
                        for x in range(number_of_steps):
                            ramp_step_temp = stepBeforeRamp.step_temp
                            ramp_step_increase = round(x, ndigits=1)
                            ramp_step_new_temp = round(stepBeforeRamp.step_temp + ramp_step_increase, ndigits=1)
                            ramp_step_time = round(x * hours_per_ramp, ndigits=1)
                            _LOGGER.debug("| #%s\t%s\t%s\t\t%s\t\t%s\t\t\t |", x, ramp_step_temp, ramp_step_increase, ramp_step_new_temp, ramp_step_time )

                        _LOGGER.debug("----------------------------------------------------------------------------")

                    time_already_ramping:timedelta = (current_step_actual_start_time_utc - currentTimeUtc)
                    hours_already_ramping  = abs((time_already_ramping.days * 24) + (time_already_ramping.seconds / 3600))
                    current_ramp_step = math.floor(hours_already_ramping / hours_per_ramp)
                    current_ramp_step_exact = hours_already_ramping / hours_per_ramp
                    temp_increase = current_ramp_step
                    _LOGGER.debug("We have been ramping %s hours, we are in ramp step: %s (%s)", round(hours_already_ramping, ndigits=2), current_ramp_step, current_ramp_step_exact)

                    if current_ramp_step > number_of_steps:
                        _LOGGER.error("Invalid temperature ramping step found!")
                        _LOGGER.debug("Somehow we have found a ramp step that is too high, ignoring any temp changes to prevent weird temperatures. Ramp step found: %s, max steps: %s", current_ramp_step, number_of_steps)

                    elif temp_increase > 0:
                        new_temp = round(stepBeforeRamp.step_temp + temp_increase, ndigits=1)
                        _LOGGER.debug("Overwrite current step temperature because of ramp to next temperature, setting temp from %s to: %s (%s)", data.current_step_temperature, new_temp, hours_per_ramp)
                        data.current_step_temperature = new_temp
        else:
            _LOGGER.error("Unable to determing current fermenting step!")

        if nextStep is not None:
            data.next_step_temperature = nextStep.step_temp

            data.next_step_date = self.datetime_fromtimestamp_with_fermentingstart(
                nextStep.actual_time, fermenting_start
            )

            _LOGGER.debug(
                "Next step: %s - %s [%s]",
                nextStep.step_temp,
                data.next_step_date,
                nextStep.ramp
            )            
        else:
            _LOGGER.debug("No next step")

        return data
        
    def datetime_fromtimestamp(self, epoch: int) -> datetime:
        return datetime.fromtimestamp(epoch / 1000, timezone.utc)

    def datetime_fromtimestamp_with_fermentingstart(
        self, epoch: int | None, fermenting_start: int | None
    ) -> datetime:
        datetime_value = self.datetime_fromtimestamp(epoch)

        if fermenting_start is not None:
            fermenting_start_date = datetime.fromtimestamp(fermenting_start / 1000)

            datetime_value += timedelta(
                hours=fermenting_start_date.hour,
                minutes=fermenting_start_date.minute,
                seconds=fermenting_start_date.second,
            )

        return datetime_value

    def get_brewfather_temp_unit(self, ha_unit: str) -> str:
        """Convert Home Assistant temperature unit to Brewfather custom stream unit."""
        if ha_unit == UnitOfTemperature.CELSIUS:
            return "C"
        elif ha_unit == UnitOfTemperature.FAHRENHEIT:
            return "F"
        elif ha_unit == UnitOfTemperature.KELVIN:
            return "K"
        else:
            _LOGGER.warning("Unsupported temperature unit '%s', defaulting to Celsius", ha_unit)
            return "C"

    async def _custom_stream_batch_active(
        self,
        fermenting_batches: list[BatchesItemElement],
    ) -> bool:
        """Return True when Brewfather can record device readings for a batch."""
        if len(fermenting_batches) > 0:
            return True
        try:
            all_batches = await self.connection.get_all_batches()
        except Exception as ex:
            _LOGGER.warning(
                "Unable to check Conditioning batches for Custom Stream: %s",
                ex,
            )
            return False
        return any(
            str(getattr(batch, "status", "") or "").lower()
            in {"fermenting", "conditioning"}
            for batch in all_batches
        )

    @staticmethod
    def _as_utc_datetime(value: Any) -> Optional[datetime]:
        """Normalize an HA/sample timestamp to timezone-aware UTC."""
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(
                    str(value).replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _state_observed_at(self, state) -> Optional[datetime]:
        """Prefer source sample time supplied by BA, then HA last_reported."""
        if state is None:
            return None
        attrs = getattr(state, "attributes", {}) or {}
        for key in (
            "brewfather_sample_observed_at",
            "source_observed_at",
            "observed_at",
        ):
            observed = self._as_utc_datetime(attrs.get(key))
            if observed is not None:
                return observed
        for attr in ("last_reported", "last_updated", "last_changed"):
            observed = self._as_utc_datetime(getattr(state, attr, None))
            if observed is not None:
                return observed
        return None

    def _fresh_numeric_state(
        self,
        state,
        *,
        now: datetime,
    ) -> Optional[float]:
        """Return a numeric state only when its underlying sample is fresh."""
        value = self._numeric_state(state)
        if value is None:
            return None
        observed_at = self._state_observed_at(state)
        if observed_at is None:
            return None
        age = max(0.0, (now - observed_at).total_seconds())
        if age > CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS:
            return None
        return value

    def _custom_stream_due(self, now: datetime) -> bool:
        """Return True when a new Custom Stream POST attempt is allowed."""
        reference_times = [
            value
            for value in (
                self.custom_stream_last_attempt_time,
                self.custom_stream_last_post_time,
            )
            if value is not None
        ]
        if not reference_times:
            return True
        latest = max(reference_times)
        elapsed = (now - latest).total_seconds()
        return elapsed >= CUSTOM_STREAM_MIN_INTERVAL_SECONDS

    @staticmethod
    def _numeric_state(state) -> Optional[float]:
        """Return one numeric HA state or None for unknown/unavailable/non-numeric."""
        if state is None or state.state in (None, "", STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
        """Convert C/F/K without introducing an extra dependency."""
        if from_unit == to_unit:
            return value

        if from_unit == UnitOfTemperature.CELSIUS:
            celsius = value
        elif from_unit == UnitOfTemperature.FAHRENHEIT:
            celsius = (value - 32.0) * 5.0 / 9.0
        elif from_unit == UnitOfTemperature.KELVIN:
            celsius = value - 273.15
        else:
            raise ValueError(f"Unsupported source temperature unit: {from_unit}")

        if to_unit == UnitOfTemperature.CELSIUS:
            return celsius
        if to_unit == UnitOfTemperature.FAHRENHEIT:
            return celsius * 9.0 / 5.0 + 32.0
        if to_unit == UnitOfTemperature.KELVIN:
            return celsius + 273.15
        raise ValueError(f"Unsupported target temperature unit: {to_unit}")

    def _temperature_entity_value(
        self,
        entity_id: Optional[str],
        target_unit: str,
        *,
        now: datetime,
        require_fresh: bool = True,
    ) -> Optional[float]:
        """Read and normalize an optional temperature entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        value = (
            self._fresh_numeric_state(state, now=now)
            if require_fresh
            else self._numeric_state(state)
        )
        if value is None or state is None:
            return None

        source_unit = state.attributes.get("unit_of_measurement")
        if source_unit not in (
            UnitOfTemperature.CELSIUS,
            UnitOfTemperature.FAHRENHEIT,
            UnitOfTemperature.KELVIN,
        ):
            _LOGGER.warning(
                "Skipping Custom Stream temperature entity %s with unsupported unit %s",
                entity_id,
                source_unit,
            )
            return None
        try:
            return round(self._convert_temperature(value, source_unit, target_unit), 3)
        except ValueError:
            return None

    def _optional_numeric_entity_value(
        self,
        entity_id: Optional[str],
        *,
        now: datetime,
        require_fresh: bool = True,
    ) -> Optional[float]:
        """Read one optional numeric entity with an optional freshness gate."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if require_fresh:
            return self._fresh_numeric_state(state, now=now)
        return self._numeric_state(state)

    def create_custom_stream_data(
        self,
        *,
        now: Optional[datetime] = None,
    ) -> Optional[custom_stream_data]:
        """Build one freshness-gated Brewfather fermentation payload."""
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        primary = self.hass.states.get(self.custom_stream_temperature_entity_name)
        primary_temp = self._fresh_numeric_state(primary, now=now)
        if primary is None or primary_temp is None:
            self.custom_stream_last_reason = (
                "primary temperature missing, invalid, or older than "
                f"{CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS} seconds"
            )
            return None

        primary_unit = primary.attributes.get("unit_of_measurement")
        if primary_unit not in (
            UnitOfTemperature.CELSIUS,
            UnitOfTemperature.FAHRENHEIT,
            UnitOfTemperature.KELVIN,
        ):
            _LOGGER.warning(
                "Custom Stream primary temperature has unsupported unit: %s",
                primary_unit,
            )
            return None

        stream_data = custom_stream_data(
            name=self.custom_stream_device_name or DEFAULT_CUSTOM_STREAM_DEVICE_NAME
        )
        stream_data.temp = primary_temp
        stream_data.temp_unit = self.get_brewfather_temp_unit(primary_unit)
        stream_data.device_source = (
            self.custom_stream_device_source or DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE
        )
        stream_data.report_source = (
            self.custom_stream_report_source or DEFAULT_CUSTOM_STREAM_REPORT_SOURCE
        )

        stream_data.aux_temp = self._temperature_entity_value(
            getattr(self, "custom_stream_aux_temperature_entity_name", None),
            primary_unit,
            now=now,
            require_fresh=True,
        )
        stream_data.ext_temp = self._temperature_entity_value(
            getattr(self, "custom_stream_ext_temperature_entity_name", None),
            primary_unit,
            now=now,
            require_fresh=True,
        )
        stream_data.temp_target = self._temperature_entity_value(
            getattr(self, "custom_stream_temp_target_entity_name", None),
            primary_unit,
            now=now,
            require_fresh=False,
        )

        stream_data.gravity = self._optional_numeric_entity_value(
            getattr(self, "custom_stream_gravity_entity_name", None),
            now=now,
            require_fresh=True,
        )
        stream_data.gravity_target = self._optional_numeric_entity_value(
            getattr(self, "custom_stream_gravity_target_entity_name", None),
            now=now,
            require_fresh=False,
        )
        if stream_data.gravity is not None or stream_data.gravity_target is not None:
            stream_data.gravity_unit = "G"

        self.custom_stream_last_reason = "fresh eligible telemetry"
        return stream_data
