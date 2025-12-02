"""Constants for the Modbus Local Gateway integration."""

from homeassistant.const import Platform
from pymodbus.framer import FramerType

DOMAIN = "modbus_local_gateway"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
]

CONF_CONNECTION_TYPES: dict[str, str] = {
    FramerType.SOCKET: "Via Gateway Device",
    FramerType.RTU: "Direct Connection",
}

CONF_DEVICE_ID = "slave_id"
CONF_DEVICE_INFO = "device_info"
CONF_DEFAULT_DEVICE_ID = 1
CONF_DEFAULT_PORT = 502
CONF_PREFIX = "prefix"
CONF_CONNECTION_TYPE = "connection_type"
CONF_DEFAULT_CONNECTION_TYPE = FramerType.SOCKET.value
OPTIONS_REFRESH = "refresh"
OPTIONS_DEFAULT_REFRESH = 30
