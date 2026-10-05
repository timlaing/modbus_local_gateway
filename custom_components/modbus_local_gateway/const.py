"""Constants for the Modbus Local Gateway integration."""

from homeassistant.const import CONF_FILENAME, Platform
from pymodbus.framer import FramerType

from .entity_management.const import WriteFunction

DOMAIN = "modbus_local_gateway"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.DATETIME,
    Platform.TIME,
    Platform.DATE,
]

CONF_CONNECTION_TYPES: dict[str, str] = {
    FramerType.SOCKET.value: "Modbus TCP",
    FramerType.RTU.value: "Modbus RTU over TCP",
}

CONF_WRITE_FUNCTION_TYPES: dict[str, str] = {
    WriteFunction.SINGLE.value: "Preset Single Register (FC 0x06)",
    WriteFunction.MULTIPLE.value: "Preset Multiple Registers (FC 0x10)",
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
OPTIONS_WRITE_FUNCTION = "write_function"
OPTIONS_DEFAULT_WRITE_FUNCTION = WriteFunction.SINGLE.value
# A device that stops answering on purpose - a solar inverter after dark - is
# not a fault, so its transitions are logged as information rather than as a
# warning. It is still probed and still goes unavailable.
OPTIONS_EXPECTED_OFFLINE = "expected_offline"
OPTIONS_DEFAULT_EXPECTED_OFFLINE = False

# The config entry is the gateway connection; every device behind it is a
# config sub-entry of that entry.
SUBENTRY_TYPE_DEVICE = "device"

# Entity ids are never renamed (issue #168). This only decides whether entities
# created from now on are *suggested* the <host>_<key> object id that
# v2026.02.0 forced onto everybody, or the name Home Assistant derives itself.
CONF_LEGACY_ENTITY_IDS = "legacy_entity_ids"
CONF_LEGACY_ENTITY_IDS_DEFAULT = True
CONF_RESTORE_ENTITY_IDS = "restore_entity_ids"

# Oldest Home Assistant this integration runs on. Config sub-entries and the
# registry arguments used to move devices and entities between them are needed
# from this release on, and `loader.py` never enforces a floor declared in the
# manifest, so `__init__.py` checks the running version itself.
MIN_HOMEASSISTANT_VERSION = "2026.9.0"

# Keys of a device sub-entry, in the order the flow asks for them.
SUBENTRY_KEYS: tuple[str, ...] = (
    CONF_PREFIX,
    CONF_DEVICE_ID,
    CONF_FILENAME,
    OPTIONS_REFRESH,
    OPTIONS_WRITE_FUNCTION,
)
