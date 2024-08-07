"""Helper functions for Modbus Local Gateway integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PREFIX, CONF_SLAVE_ID, DOMAIN
from .coordinator import ModbusContext, ModbusCoordinator
from .sensor_types.const import ControlType
from .sensor_types.device_loader import create_device_info
from .sensor_types.modbus_device_info import ModbusDeviceInfo

_LOGGER: logging.Logger = logging.getLogger(__name__)


def get_gateway_key(entry: ConfigEntry, with_slave: bool = True) -> str:
    """Get the gateway key for the coordinator"""
    if with_slave:
        return f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}:{entry.data[CONF_SLAVE_ID]}"

    return f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"


def get_prefix(config: dict[str, Any]) -> str:
    """Gets the sensor entity id prefix"""
    prefix: str = config.get(CONF_PREFIX, "")
    if prefix != "":
        return f"{prefix}-"
    return prefix


async def async_setup_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    control: ControlType,
    entity_class: CoordinatorEntity,
) -> None:
    """Set up the Modbus Local Gateway sensor."""
    config: dict[str, Any] = {**config_entry.data}
    _LOGGER.debug(config)
    coordinator: ModbusCoordinator = hass.data[DOMAIN][get_gateway_key(config_entry)]
    device_info: ModbusDeviceInfo = await hass.async_add_executor_job(
        create_device_info, config[CONF_FILENAME]
    )

    coordinator.max_read_size = device_info.max_read_size

    identifiers: set[tuple[str, str]] = {
        (DOMAIN, f"{coordinator.gateway}-{config[CONF_SLAVE_ID]}"),
    }

    device = DeviceInfo(
        identifiers=identifiers,
        name=f"{get_prefix(config)}{device_info.model}",
        manufacturer=device_info.manufacturer,
        model=device_info.model,
        via_device=list(coordinator.gateway_device.identifiers)[0],
    )

    _LOGGER.debug(device)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [
            entity_class(
                coordinator=coordinator,
                ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID], desc=desc),
                device=device,
            )
            for desc in device_info.entity_desciptions
            if desc.control_type == control
        ]
        + [
            entity_class(
                coordinator=coordinator,
                ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID], desc=desc),
                device=device,
            )
            for desc in device_info.properties
            if desc.control_type == control
        ],
        update_before_add=False,
    )
