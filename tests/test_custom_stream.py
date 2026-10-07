"""Custom Stream regression tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    CUSTOM_STREAM_MIN_INTERVAL_SECONDS,
    LOG_CUSTOM_STREAM,
)
from custom_components.brewfather.coordinator import BrewfatherCoordinator
from custom_components.brewfather.models.custom_stream_data import custom_stream_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature


class FakeState:
    def __init__(self, state, unit=None):
        self.state = state
        self.attributes = {}
        if unit is not None:
            self.attributes["unit_of_measurement"] = unit


class FakeStates:
    def __init__(self, values):
        self._values = values

    def get(self, entity_id):
        return self._values.get(entity_id)


class FakeHass:
    def __init__(self, values):
        self.states = FakeStates(values)


def _coordinator() -> BrewfatherCoordinator:
    hass = FakeHass(
        {
            "sensor.pill_temp": FakeState("20.2", UnitOfTemperature.CELSIUS),
            "sensor.coolant_f": FakeState("41.0", UnitOfTemperature.FAHRENHEIT),
            "sensor.room_temp": FakeState("22.3", UnitOfTemperature.CELSIUS),
            "sensor.target_temp": FakeState("20.5", UnitOfTemperature.CELSIUS),
            "sensor.gravity": FakeState("1.012"),
            "sensor.target_fg": FakeState("1.010"),
        }
    )
    entry = SimpleNamespace(
        data={
            CONF_USERNAME: "user",
            CONF_PASSWORD: "key",
            CONF_CUSTOM_STREAM_ENABLED: True,
            CONF_CUSTOM_STREAM_LOGGING_ID: "logging-id",
            CONF_CUSTOM_STREAM_DEVICE_NAME: "BrewAssistant GF30",
            CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME: "sensor.pill_temp",
            CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME: "sensor.coolant_f",
            CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME: "sensor.room_temp",
            CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME: "sensor.target_temp",
            CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME: "sensor.gravity",
            CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME: "sensor.target_fg",
            CONF_CUSTOM_STREAM_DEVICE_SOURCE: "RAPT Pill + BrewAssistant GF30",
            CONF_CUSTOM_STREAM_REPORT_SOURCE: "Home Assistant",
        }
    )
    return BrewfatherCoordinator(hass, entry, timedelta(minutes=15))


def test_custom_stream_uses_https_and_15_minimum_interval() -> None:
    assert LOG_CUSTOM_STREAM.startswith("https://")
    assert CUSTOM_STREAM_MIN_INTERVAL_SECONDS == 900


def test_custom_stream_builds_gf30_fermentation_payload() -> None:
    coordinator = _coordinator()

    payload = coordinator.create_custom_stream_data()

    assert payload is not None
    assert payload.name == "BrewAssistant GF30"
    assert payload.temp == 20.2
    assert payload.temp_unit == "C"
    assert payload.aux_temp == 5.0
    assert payload.ext_temp == 22.3
    assert payload.temp_target == 20.5
    assert payload.gravity == 1.012
    assert payload.gravity_target == 1.010
    assert payload.gravity_unit == "G"
    assert payload.device_source == "RAPT Pill + BrewAssistant GF30"
    assert payload.report_source == "Home Assistant"


def test_custom_stream_rate_gate_is_independent_of_coordinator_refreshes() -> None:
    coordinator = _coordinator()
    now = datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc)

    assert coordinator._custom_stream_due(now) is True

    coordinator.custom_stream_last_post_time = now
    assert coordinator._custom_stream_due(now + timedelta(seconds=899)) is False
    assert coordinator._custom_stream_due(now + timedelta(seconds=900)) is True


def test_custom_stream_payload_omits_unset_optional_fields() -> None:
    connection = Connection("user", "key")
    payload = custom_stream_data("BrewAssistant GF30")
    payload.temp = 20.0
    payload.temp_unit = "C"

    as_dict = connection.to_dict(payload)

    assert as_dict == {
        "name": "BrewAssistant GF30",
        "temp": 20.0,
        "temp_unit": "C",
    }


def test_custom_stream_update_contract_is_fermentation_only_and_best_effort() -> None:
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/coordinator.py"
    ).read_text(encoding="utf-8")

    assert "and len(allBatches) > 0" in source
    assert "and self._custom_stream_due" in source
    assert "Custom stream POST failed; continuing normal update" in source
    assert "self.custom_stream_last_post_time = datetime.now(timezone.utc)" in source


def test_custom_stream_does_not_forward_brewfather_api_credentials() -> None:
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/connection.py"
    ).read_text(encoding="utf-8")

    block = source.split("async def post_custom_stream", 1)[1].split("def to_dict", 1)[0]
    assert "session.post(url, json=payload)" in block
    assert "auth=self.auth" not in block


def test_custom_stream_configuration_does_not_send_fake_reading() -> None:
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "custom_components/brewfather/config_flow.py"
    ).read_text(encoding="utf-8")

    assert "without sending a test reading" in source
    assert "validate/extract logging ID without creating a fake Brewfather log" in source


def test_custom_stream_model_uses_published_fermentation_field_names() -> None:
    payload = custom_stream_data("BrewAssistant GF30")

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
