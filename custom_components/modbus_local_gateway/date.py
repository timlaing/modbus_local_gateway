"""Modbus Local Gateway dates"""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import cast

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusDateEntityDescription
from .entity_management.const import ControlType
from .helpers import async_setup_entities

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway entities."""
    # Home Assistant hands the state to every platform setup; the entities of a
    # device come from the sub-entries the entry already holds.
    async_setup_entities(
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        control=ControlType.DATE,
        entity_class=ModbusDateEntity,
    )


class ModbusDateEntity(ModbusCoordinatorEntity, DateEntity):
    """Date entity for Modbus gateway"""

    entity_description: ModbusDateEntityDescription

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a Modbus date."""
        super().__init__(coordinator, ctx=ctx, device=device)
        self._attr_native_value: date | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: date | None = cast(
                "date | None",
                self.coordinator.get_data(self.coordinator_context),
            )
            # A datetime is a date as far as isinstance is concerned, and a date
            # entity has no way of showing the time of day with it.
            if isinstance(value, date) and not isinstance(value, datetime):
                self._attr_native_value = value
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    self._attr_native_value,
                )
            super()._handle_coordinator_update()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_value(self, value: date) -> None:
        """Set a new value in the entity. Not used, updates are async."""
        raise NotImplementedError()

    async def async_set_value(self, value: date) -> None:
        """Write a new date to the device."""
        if isinstance(self.coordinator, ModbusCoordinator) and isinstance(
            self.entity_description, ModbusDateEntityDescription
        ):
            await self.write_data(value)
