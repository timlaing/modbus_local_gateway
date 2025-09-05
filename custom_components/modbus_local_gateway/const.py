"""Constants for the Modbus Local Gateway integration."""

from homeassistant.const import Platform

DOMAIN = "modbus_local_gateway"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
]

CONF_DEVICE_ID = "slave_id"
CONF_DEVICE_INFO = "device_info"
CONF_DEFAULT_DEVICE_ID = 1
CONF_DEFAULT_PORT = 502
CONF_PREFIX = "prefix"
OPTIONS_REFRESH = "refresh"
OPTIONS_DEFAULT_REFRESH = 30
