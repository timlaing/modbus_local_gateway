"""Modbus Local Gateway datetimes"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import cast

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusDateTimeEntityDescription
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
        control=ControlType.DATETIME,
        entity_class=ModbusDateTimeEntity,
    )


class ModbusDateTimeEntity(ModbusCoordinatorEntity, DateTimeEntity):
    """Date time entity for Modbus gateway"""

    entity_description: ModbusDateTimeEntityDescription

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a Modbus datetime."""
        super().__init__(coordinator, ctx=ctx, device=device)
        self._attr_native_value: datetime | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: datetime | None = cast(
                "datetime | None",
                self.coordinator.get_data(self.coordinator_context),
            )
            if isinstance(value, datetime):
                self._attr_native_value = value
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    self._attr_native_value,
                )
            super()._handle_coordinator_update()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_value(self, value: datetime) -> None:
        """Set a new value in the entity. Not used, updates are async."""
        raise NotImplementedError()

    async def async_set_value(self, value: datetime) -> None:
        """Write a new date and time to the device."""
        if isinstance(self.coordinator, ModbusCoordinator) and isinstance(
            self.entity_description, ModbusDateTimeEntityDescription
        ):
            await self.write_data(value)
