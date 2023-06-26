"""Constants for the Modbus Local Gateway integration."""
from homeassistant.const import Platform

DOMAIN = "modbus_local_gateway"

PLATFORMS = [Platform.SENSOR]

CONF_SLAVE_ID = "slave_id"
CONF_DEVICE_INFO = "device_info"
CONF_DEFAULT_SLAVE_ID = 1
CONF_DEFAULT_PORT = 8899
OPTIONS_REFRESH = "refresh"
OPTIONS_DEFAULT_REFRESH = 30