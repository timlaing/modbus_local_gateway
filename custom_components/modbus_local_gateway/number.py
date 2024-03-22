"""Modbus Local Gateway number control"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILENAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PREFIX, CONF_SLAVE_ID, DOMAIN
from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import get_gateway_key
from .sensor_types.base import ModbusNumberEntityDescription
from .sensor_types.const import ControlType
from .sensor_types.conversion import Conversion
from .sensor_types.modbus_device_info import ModbusDeviceInfo

_LOGGER = logging.getLogger(__name__)


def get_prefix(config: dict[str, Any]) -> str:
    """Gets the sensor entity id prefix"""
    prefix = config.get(CONF_PREFIX, "")
    if prefix != "":
        return f"{prefix}-"
    return prefix


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway sensor."""
    config: dict[str, Any] = {**config_entry.data}
    _LOGGER.debug(config)
    coordinator: ModbusCoordinator = hass.data[DOMAIN][get_gateway_key(config_entry)]
    device_info: ModbusDeviceInfo = ModbusDeviceInfo(config[CONF_FILENAME])

    coordinator.max_read_size = device_info.max_read_size

    identifiers = {
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
            ModbusNumberEntity(
                coordinator=coordinator,
                ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID], desc=desc),
                device=device,
            )
            for desc in device_info.properties
            if desc.control_type == ControlType.NUMBER
        ],
        update_before_add=False,
    )


class ModbusNumberEntity(CoordinatorEntity, NumberEntity):
    """Number entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput number."""
        super().__init__(coordinator, context=ctx)
        self.entity_description: ModbusNumberEntityDescription = ctx.desc
        self._attr_unique_id: str = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo = device
        self._attr_max_value: float = ctx.desc.max
        self._attr_min_value: float = ctx.desc.min
        self._attr_mode = NumberMode.BOX

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_data(self.coordinator_context)
            if value is not None:
                self._attr_native_value = value
                self.async_write_ha_state()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_native_value(self, value: float) -> None:
        """Set new value."""
        raise NotImplementedError()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if isinstance(self.coordinator, ModbusCoordinator):
            registers = Conversion(self.coordinator.client).convert_to_registers(
                value=value, desc=self.entity_description
            )

            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=registers
            )
