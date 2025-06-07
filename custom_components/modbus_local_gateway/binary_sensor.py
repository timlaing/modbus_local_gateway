"""Modbus Local Gateway binary sensors"""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusBinarySensorEntityDescription
from .entity_management.const import ControlType
from .helpers import async_setup_entities

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway binary sensors."""
    await async_setup_entities(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        control=ControlType.BINARY_SENSOR,
        entity_class=ModbusBinarySensorEntity,
    )


class ModbusBinarySensorEntity(ModbusCoordinatorEntity, BinarySensorEntity):  # type: ignore
    """Binary sensor entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a Modbus binary sensor."""
        super().__init__(coordinator, ctx=ctx, device=device)
        if not isinstance(ctx.desc, ModbusBinarySensorEntityDescription):
            raise TypeError("Invalid description type")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = cast(ModbusCoordinator, self.coordinator).get_data(
                self.coordinator_context
            )
            if (
                value is not None
                and isinstance(value, (int | bool))
                and isinstance(
                    self.entity_description, ModbusBinarySensorEntityDescription
                )
            ):
                self._attr_is_on = value == self.entity_description.on
            else:
                raise ValueError("Invalid value for binary sensor")
            _LOGGER.debug(
                "Updating device with %s as %s",
                self.entity_description.key,
                self._attr_is_on,
            )
            super()._handle_coordinator_update()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)
