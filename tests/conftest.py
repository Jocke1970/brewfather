"""pytest configuration for Brewfather tests."""
import sys
from types import ModuleType
from unittest.mock import MagicMock


class _GenericEntity:
    """Minimal Home Assistant entity stub used by unit tests."""

    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, *args, **kwargs):
        if args:
            self.coordinator = args[0]
        self.entity_id = "test_entity"
        self.device_class = None


class _DataUpdateCoordinator:
    """Minimal generic DataUpdateCoordinator stub."""

    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, *args, **kwargs):
        self.hass = args[0] if args else None
        self.data = None
        self.last_update_success = True


class _SensorEntityDescription:
    """Minimal SensorEntityDescription stub."""

    def __init__(self, **kwargs):
        self.key = kwargs.get("key")
        self.name = kwargs.get("name")
        self.icon = kwargs.get("icon")
        self.native_unit_of_measurement = kwargs.get("native_unit_of_measurement")
        self.device_class = kwargs.get("device_class")
        self.state_class = kwargs.get("state_class")


def _callback(func):
    return func


# Mock all external dependencies for tests that don't need a full Home Assistant runtime.
def mock_dependencies():
    """Mock external dependencies."""
    homeassistant = ModuleType("homeassistant")
    ha_const = ModuleType("homeassistant.const")
    ha_config_entries = ModuleType("homeassistant.config_entries")
    ha_core = ModuleType("homeassistant.core")
    ha_exceptions = ModuleType("homeassistant.exceptions")
    ha_helpers = ModuleType("homeassistant.helpers")
    ha_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    ha_event = ModuleType("homeassistant.helpers.event")
    ha_entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    ha_typing = ModuleType("homeassistant.helpers.typing")
    ha_components = ModuleType("homeassistant.components")
    ha_sensor = ModuleType("homeassistant.components.sensor")

    # Constants and simple HA types used while importing the integration.
    ha_const.CONF_PASSWORD = "password"
    ha_const.CONF_USERNAME = "username"
    ha_const.PERCENTAGE = "%"
    ha_const.Platform = MagicMock()
    ha_const.STATE_UNKNOWN = "unknown"
    ha_const.STATE_UNAVAILABLE = "unavailable"
    ha_const.UnitOfTemperature = MagicMock(
        CELSIUS="°C",
        FAHRENHEIT="°F",
        KELVIN="K",
    )

    ha_core.HomeAssistant = MagicMock
    ha_core.callback = _callback
    ha_config_entries.ConfigEntry = MagicMock
    ha_exceptions.ConfigEntryNotReady = RuntimeError

    ha_update_coordinator.CoordinatorEntity = _GenericEntity
    ha_update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
    ha_update_coordinator.UpdateFailed = RuntimeError

    ha_event.async_track_state_change_event = MagicMock()
    ha_entity_platform.AddEntitiesCallback = MagicMock
    ha_typing.StateType = object

    ha_sensor.SensorEntity = _GenericEntity
    ha_sensor.SensorEntityDescription = _SensorEntityDescription
    ha_sensor.SensorStateClass = MagicMock(MEASUREMENT="measurement")
    ha_sensor.SensorDeviceClass = MagicMock(
        TEMPERATURE="temperature",
        TIMESTAMP="timestamp",
    )

    homeassistant.const = ha_const
    homeassistant.config_entries = ha_config_entries
    homeassistant.core = ha_core
    homeassistant.exceptions = ha_exceptions
    homeassistant.helpers = ha_helpers
    homeassistant.components = ha_components
    ha_helpers.update_coordinator = ha_update_coordinator
    ha_helpers.event = ha_event
    ha_helpers.entity_platform = ha_entity_platform
    ha_helpers.typing = ha_typing
    ha_components.sensor = ha_sensor

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.exceptions"] = ha_exceptions
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_update_coordinator
    sys.modules["homeassistant.helpers.event"] = ha_event
    sys.modules["homeassistant.helpers.entity_platform"] = ha_entity_platform
    sys.modules["homeassistant.helpers.typing"] = ha_typing
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.sensor"] = ha_sensor

    # External libraries used by the integration.
    sys.modules["aiohttp"] = MagicMock()


# Mock dependencies before any integration imports happen.
mock_dependencies()
