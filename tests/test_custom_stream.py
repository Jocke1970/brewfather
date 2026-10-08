"""Custom Stream regression tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from custom_components.brewfather.connection import Connection
from custom_components.brewfather.const import (
    CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_DEVICE_NAME,
    CONF_CUSTOM_STREAM_DEVICE_SOURCE,
    CONF_CUSTOM_STREAM_ENABLED,
    CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME,
    CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME,
    CONF_CUSTOM_STREAM_LOGGING_ID,
    CONF_CUSTOM_STREAM_REPORT_SOURCE,
    CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME,
    CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME,
    CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS,
    CUSTOM_STREAM_MIN_INTERVAL_SECONDS,
    DEFAULT_CUSTOM_STREAM_DEVICE_NAME,
    DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE,
    LOG_CUSTOM_STREAM,
)
from custom_components.brewfather.coordinator import BrewfatherCoordinator
from custom_components.brewfather.models.custom_stream_data import custom_stream_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature


NOW = datetime(2026, 10, 8, 20, 0, tzinfo=timezone.utc)


class FakeState:
    def __init__(
        self,
        state,
        unit=None,
        *,
        observed_at: datetime | None = NOW,
        sample_observed_at: datetime | None = None,
    ):
        self.state = state
        self.attributes = {}
        if unit is not None:
            self.attributes["unit_of_measurement"] = unit
        if sample_observed_at is not None:
            self.attributes["brewfather_sample_observed_at"] = (
                sample_observed_at.isoformat()
            )
        self.last_reported = observed_at
        self.last_updated = observed_at
        self.last_changed = observed_at


class FakeStates:
    def __init__(self, values):
        self._values = values

    def get(self, entity_id):
        return self._values.get(entity_id)


class FakeHass:
    def __init__(self, values):
        self.states = FakeStates(values)


def _coordinator(
    *,
    primary_observed_at: datetime = NOW,
    gravity_observed_at: datetime = NOW,
    aux_observed_at: datetime = NOW,
) -> BrewfatherCoordinator:
    hass = FakeHass(
        {
            "sensor.ba_temp": FakeState(
                "20.2",
                UnitOfTemperature.CELSIUS,
                observed_at=primary_observed_at,
                sample_observed_at=primary_observed_at,
            ),
            "sensor.ba_aux": FakeState(
                "5.0",
                UnitOfTemperature.CELSIUS,
                observed_at=aux_observed_at,
                sample_observed_at=aux_observed_at,
            ),
            "sensor.room_temp": FakeState(
                "22.3",
                UnitOfTemperature.CELSIUS,
                observed_at=aux_observed_at,
            ),
            "sensor.ba_target": FakeState(
                "20.5",
                UnitOfTemperature.CELSIUS,
                observed_at=NOW - timedelta(days=3),
            ),
            "sensor.ba_gravity": FakeState(
                "1.012",
                observed_at=gravity_observed_at,
                sample_observed_at=gravity_observed_at,
            ),
            "sensor.ba_target_fg": FakeState(
                "1.010",
                observed_at=NOW - timedelta(days=3),
            ),
        }
    )
    entry = SimpleNamespace(
        data={
            CONF_USERNAME: "user",
            CONF_PASSWORD: "key",
            CONF_CUSTOM_STREAM_ENABLED: True,
            CONF_CUSTOM_STREAM_LOGGING_ID: "logging-id",
            CONF_CUSTOM_STREAM_DEVICE_NAME: "BrewAssistant Fermentation",
            CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME: "sensor.ba_temp",
            CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME: "sensor.ba_aux",
            CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME: "sensor.room_temp",
            CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME: "sensor.ba_target",
            CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME: "sensor.ba_gravity",
            CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME: "sensor.ba_target_fg",
            CONF_CUSTOM_STREAM_DEVICE_SOURCE: "BrewAssistant",
            CONF_CUSTOM_STREAM_REPORT_SOURCE: "Home Assistant",
        }
    )
    return BrewfatherCoordinator(hass, entry, timedelta(minutes=15))


def test_custom_stream_uses_https_and_local_safety_intervals() -> None:
    assert LOG_CUSTOM_STREAM.startswith("https://")
    assert CUSTOM_STREAM_MIN_INTERVAL_SECONDS == 900
    assert CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS == 1200


def test_custom_stream_defaults_are_provider_neutral() -> None:
    assert DEFAULT_CUSTOM_STREAM_DEVICE_NAME == "BrewAssistant Fermentation"
    assert DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE == "BrewAssistant"


def test_custom_stream_builds_normalized_fermentation_payload() -> None:
    coordinator = _coordinator()

    payload = coordinator.create_custom_stream_data(now=NOW)

    assert payload is not None
    assert payload.name == "BrewAssistant Fermentation"
    assert payload.temp == 20.2
    assert payload.temp_unit == "C"
    assert payload.aux_temp == 5.0
    assert payload.ext_temp == 22.3
    assert payload.temp_target == 20.5
    assert payload.gravity == 1.012
    assert payload.gravity_target == 1.010
    assert payload.gravity_unit == "G"
    assert payload.device_source == "BrewAssistant"
    assert payload.report_source == "Home Assistant"
    assert coordinator.custom_stream_last_reason == "fresh eligible telemetry"


def test_custom_stream_prefers_brewassistant_sample_timestamp() -> None:
    stale_sample = NOW - timedelta(seconds=CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS + 1)
    coordinator = _coordinator()
    state = coordinator.hass.states.get("sensor.ba_temp")
    state.last_reported = NOW
    state.last_updated = NOW
    state.attributes["brewfather_sample_observed_at"] = stale_sample.isoformat()

    assert coordinator.create_custom_stream_data(now=NOW) is None
    assert "older than" in coordinator.custom_stream_last_reason


def test_stale_primary_temperature_blocks_entire_payload() -> None:
    stale = NOW - timedelta(seconds=CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS + 1)
    coordinator = _coordinator(primary_observed_at=stale)

    payload = coordinator.create_custom_stream_data(now=NOW)

    assert payload is None
    assert "primary temperature" in coordinator.custom_stream_last_reason


def test_stale_optional_measurements_are_omitted_but_targets_remain() -> None:
    stale = NOW - timedelta(seconds=CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS + 1)
    coordinator = _coordinator(
        gravity_observed_at=stale,
        aux_observed_at=stale,
    )

    payload = coordinator.create_custom_stream_data(now=NOW)

    assert payload is not None
    assert payload.temp == 20.2
    assert payload.gravity is None
    assert payload.aux_temp is None
    assert payload.ext_temp is None
    assert payload.temp_target == 20.5
    assert payload.gravity_target == 1.010
    assert payload.gravity_unit == "G"


def test_custom_stream_rate_gate_is_independent_of_coordinator_refreshes() -> None:
    coordinator = _coordinator()

    assert coordinator._custom_stream_due(NOW) is True

    coordinator.custom_stream_last_attempt_time = NOW
    assert coordinator._custom_stream_due(NOW + timedelta(seconds=899)) is False
    assert coordinator._custom_stream_due(NOW + timedelta(seconds=900)) is True


def test_custom_stream_payload_omits_unset_optional_fields() -> None:
    connection = Connection("user", "key")
    payload = custom_stream_data("BrewAssistant Fermentation")
    payload.temp = 20.0
    payload.temp_unit = "C"

    as_dict = connection.to_dict(payload)

    assert as_dict == {
        "name": "BrewAssistant Fermentation",
        "temp": 20.0,
        "temp_unit": "C",
    }


def test_custom_stream_update_contract_is_batch_scoped_and_best_effort() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/coordinator.py"
    ).read_text(encoding="utf-8")

    assert "_custom_stream_batch_active" in source
    assert '"fermenting", "conditioning"' in source
    assert 'self.custom_stream_last_result = "throttled"' in source
    assert 'self.custom_stream_last_result = "inactive_batch"' in source
    assert 'self.custom_stream_last_result = "not_eligible"' in source
    assert 'self.custom_stream_last_result = "sent"' in source
    assert "Custom stream POST failed; continuing normal update" in source


def test_custom_stream_does_not_forward_brewfather_api_credentials() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/connection.py"
    ).read_text(encoding="utf-8")

    block = source.split("async def post_custom_stream", 1)[1].split(
        "def to_dict", 1
    )[0]
    assert "session.post(url, json=payload)" in block
    assert "auth=self.auth" not in block
    assert "response from {url}" not in block


def test_legacy_custom_stream_validation_is_non_mutating() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/connection.py"
    ).read_text(encoding="utf-8")

    block = source.split("async def test_custom_stream", 1)[1].split(
        "async def get_batches", 1
    )[0]
    assert "return bool(str(logging_id or \"\").strip())" in block
    assert "session.post" not in block
    assert "fake device reading" in block


def test_custom_stream_configuration_does_not_send_fake_reading_or_log_secret() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/config_flow.py"
    ).read_text(encoding="utf-8")

    assert "without sending a test reading" in source
    assert "validate/extract logging id without creating a fake brewfather log" in source.lower()
    assert "Successfully extracted logging ID '%s'" not in source
    assert '"URL does not appear to be a Brewfather URL: %s"' not in source


def test_custom_stream_status_sensor_exposes_delivery_diagnostics_without_id() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/sensor.py"
    ).read_text(encoding="utf-8")

    assert '"custom_stream_last_result"' in source
    assert '"custom_stream_last_reason"' in source
    assert '"custom_stream_last_attempt"' in source
    assert '"custom_stream_last_success"' in source
    assert '"custom_stream_last_payload_fields"' in source
    status_block = source.split("class BrewfatherStatusSensor", 1)[1].split(
        "async def async_setup_entry", 1
    )[0]
    assert "custom_stream_logging_id" not in status_block


def test_custom_stream_model_uses_published_fermentation_field_names() -> None:
    payload = custom_stream_data("BrewAssistant Fermentation")

    for field in (
        "temp",
        "aux_temp",
        "ext_temp",
        "temp_unit",
        "gravity",
        "gravity_unit",
        "temp_target",
        "gravity_target",
        "device_source",
        "report_source",
    ):
        assert hasattr(payload, field)


def test_custom_stream_does_not_emit_gravity_unit_without_gravity_data() -> None:
    connection = Connection("user", "key")
    payload = custom_stream_data("BrewAssistant Fermentation")
    payload.temp = 20.0
    payload.temp_unit = "C"

    as_dict = connection.to_dict(payload)

    assert "gravity" not in as_dict
    assert "gravity_unit" not in as_dict
    assert "gravity_target" not in as_dict



def test_custom_stream_rate_gate_uses_latest_attempt_or_success() -> None:
    coordinator = _coordinator()
    coordinator.custom_stream_last_post_time = NOW
    coordinator.custom_stream_last_attempt_time = NOW + timedelta(seconds=30)

    assert coordinator._custom_stream_due(NOW + timedelta(seconds=929)) is False
    assert coordinator._custom_stream_due(NOW + timedelta(seconds=930)) is True


def test_custom_stream_config_accepts_temporarily_unavailable_sources() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/config_flow.py"
    ).read_text(encoding="utf-8")

    assert "may legitimately be inactive between" in source
    assert "Runtime freshness/numeric validation" in source
    assert 'if entity.state in ("unknown", "unavailable", None, ""):' in source
    assert "return None" in source


def test_custom_stream_malformed_url_is_rejected_without_echoing_secret() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/config_flow.py"
    ).read_text(encoding="utf-8")

    assert 'return ""' in source
    assert "Successfully extracted Brewfather Custom Stream logging ID" in source
    assert "input_value" not in source.split(
        "def extract_logging_id_from_url", 1
    )[1].split("def validate_temperature_unit", 1)[0].replace(
        "input_value.startswith", ""
    )
