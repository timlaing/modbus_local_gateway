"""Helper functions for Growatt Modbus Local integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_SLAVE_ID


_LOGGER = logging.getLogger(__name__)

def get_gateway_key(entry: ConfigEntry, with_slave: bool = True) -> str:
    """Get the gateway key for the coordinator"""
    if with_slave:
        return f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}:{entry.data[CONF_SLAVE_ID]}"

    return f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
