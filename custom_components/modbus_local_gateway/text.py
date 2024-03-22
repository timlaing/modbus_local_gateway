"""Modbus Local Gateway text control"""

from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import async_setup_entities
from .sensor_types.base import ModbusTextEntityDescription
from .sensor_types.const import ControlType
from .sensor_types.conversion import Conversion

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway entities."""
    await async_setup_entities(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        control=ControlType.TEXT,
        entity_class=ModbusTextEntity,
    )


class ModbusTextEntity(CoordinatorEntity, TextEntity):
    """Text entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput string."""
        super().__init__(coordinator, context=ctx)
        self.entity_description: ModbusTextEntityDescription = ctx.desc
        self._attr_unique_id: str = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo = device

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_data(self.coordinator_context)
            if value is not None:
                self._attr_state = value
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )
                self.async_write_ha_state()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_value(self, value: str) -> None:
        """Set new value."""
        raise NotImplementedError()

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        if isinstance(self.coordinator, ModbusCoordinator):
            registers = Conversion(self.coordinator.client).convert_to_registers(
                value=value, desc=self.entity_description
            )

            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=registers
            )
