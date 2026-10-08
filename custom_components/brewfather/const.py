DOMAIN = "brewfather"
COORDINATOR = "coordinator"

UPDATE_INTERVAL = 900 #15 minutes
CUSTOM_STREAM_MIN_INTERVAL_SECONDS = 900
CUSTOM_STREAM_MAX_SAMPLE_AGE_SECONDS = 1200
MS_IN_DAY = 86400000

TEST_URI = "https://api.brewfather.app/v2/batches/"
ALL_BATCHES_URI = "https://api.brewfather.app/v2/batches/"
BATCHES_URI = "https://api.brewfather.app/v2/batches/?status=Fermenting"
BATCH_URI = "https://api.brewfather.app/v2/batches/{}?include=recipe.fermentation,notes,measuredOg,batchNotes,events"
READINGS_URI = "https://api.brewfather.app/v2/batches/{}/readings"
LAST_READING_URI = "https://api.brewfather.app/v2/batches/{}/readings/last"
BREWTRACKER_URI = "https://api.brewfather.app/v2/batches/{}/brewtracker"
LOG_CUSTOM_STREAM = "https://log.brewfather.net/stream?id={}"

DRY_RUN = False
CONF_RAMP_TEMP_CORRECTION = "ramp_temp_correction"
CONF_MULTI_BATCH = "multi_batch"
CONF_ALL_BATCH_INFO_SENSOR = "all_batch_info_sensor"
CONF_CUSTOM_STREAM_ENABLED = "custom_stream_enabled"
CONF_CUSTOM_STREAM_LOGGING_ID = "custom_stream_logging_id"
CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_NAME = "custom_stream_temperature_entity_name"
CONF_CUSTOM_STREAM_TEMPERATURE_ENTITY_ATTRIBUTE = "custom_stream_temperature_entity_attribute"
CONF_CUSTOM_STREAM_GRAVITY_ENTITY_NAME = "custom_stream_gravity_entity_name"
CONF_CUSTOM_STREAM_DEVICE_NAME = "custom_stream_device_name"
CONF_CUSTOM_STREAM_AUX_TEMPERATURE_ENTITY_NAME = "custom_stream_aux_temperature_entity_name"
CONF_CUSTOM_STREAM_EXT_TEMPERATURE_ENTITY_NAME = "custom_stream_ext_temperature_entity_name"
CONF_CUSTOM_STREAM_TEMP_TARGET_ENTITY_NAME = "custom_stream_temp_target_entity_name"
CONF_CUSTOM_STREAM_GRAVITY_TARGET_ENTITY_NAME = "custom_stream_gravity_target_entity_name"
CONF_CUSTOM_STREAM_DEVICE_SOURCE = "custom_stream_device_source"
CONF_CUSTOM_STREAM_REPORT_SOURCE = "custom_stream_report_source"

DEFAULT_CUSTOM_STREAM_DEVICE_NAME = "BrewAssistant Fermentation"
DEFAULT_CUSTOM_STREAM_DEVICE_SOURCE = "BrewAssistant"
DEFAULT_CUSTOM_STREAM_REPORT_SOURCE = "Home Assistant"

VERSION_MAJOR = 1
VERSION_MINOR = 4
