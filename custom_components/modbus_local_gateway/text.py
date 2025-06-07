"""Modbus Local Gateway text control"""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.const import ControlType
from .helpers import async_setup_entities

_LOGGER: logging.Logger = logging.getLogger(__name__)


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


class ModbusTextEntity(ModbusCoordinatorEntity, TextEntity):  # type: ignore
    """Text entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput sensor."""
        super().__init__(coordinator, ctx=ctx, device=device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if value is not None:
                self._attr_native_value = str(value)
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )
            super()._handle_coordinator_update()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_value(self, value: str) -> None:
        """Set new value."""
        raise NotImplementedError()

    async def async_set_value(self, value: str) -> None:
        """Set new value."""
        if isinstance(self.coordinator, ModbusCoordinator):
            await self.write_data(value)
