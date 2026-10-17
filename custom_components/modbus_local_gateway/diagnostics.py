"""Diagnostics for the Modbus Local Gateway integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVICE,
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_SERIAL_NUMBER,
    SUBENTRY_TYPE_DEVICE,
    TRANSPORT_SERIAL_PROXY,
)
from .helpers import get_connection_type, get_transport
from .serial_proxy import serialx_available

# What says where an installation is rather than how it works. A host, a
# port URL and a serial number end up in reports pasted into issues, so
# they go; everything that decides whether a connection works stays.
TO_REDACT = (CONF_DEVICE, CONF_HOST, CONF_SERIAL_NUMBER)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics about the gateway connection of one config entry.

    A report needs to say how the gateway is reached and at what settings:
    the transport, the framer, the UART settings of a serial line and what
    devices are behind the gateway are all kept. Only where the gateway is
    is left out of what a user would paste into an issue.
    """
    data: dict[str, Any] = {
        "state": entry.state.value,
        "version": entry.version,
        "transport": get_transport(entry.data),
        "connection_type": get_connection_type(entry.data),
        "legacy_entity_ids": bool(
            entry.data.get(CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT)
        ),
        "devices": len(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)),
        "settings": async_redact_data(dict(entry.data), TO_REDACT),
    }
    if get_transport(entry.data) == TRANSPORT_SERIAL_PROXY:
        # Whether the library that opens proxy ports is installed at all is
        # the first thing to know when a serial gateway does not work. An
        # `importlib` spec lookup touches the filesystem, so it runs off the
        # event loop.
        data["serial_support"] = await hass.async_add_executor_job(serialx_available)
    return data
