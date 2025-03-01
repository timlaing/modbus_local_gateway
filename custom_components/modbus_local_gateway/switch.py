"""Modbus Local Gateway switches"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .helpers import async_setup_entities
from .entity_management.base import ModbusSwitchEntityDescription
from .entity_management.const import ControlType, ModbusDataType

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
        control=ControlType.SWITCH,
        entity_class=ModbusSwitchEntity,
    )


class ModbusSwitchEntity(ModbusCoordinatorEntity, SwitchEntity):
    """Switch entity for Modbus gateway"""

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
            value: str | int | bool | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if value is not None and isinstance(
                self.entity_description, ModbusSwitchEntityDescription
            ):
                if self.entity_description.data_type == ModbusDataType.COIL:
                    self._attr_is_on = value
                elif self.entity_description.data_type == ModbusDataType.HOLDING_REGISTER:
                    self._attr_is_on = value == self.entity_description.on
                else:
                    raise ValueError("Invalid data_type for switch")
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )
                self.async_write_ha_state()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        raise NotImplementedError()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if isinstance(self.coordinator, ModbusCoordinator) and isinstance(
            self.entity_description, ModbusSwitchEntityDescription
        ):
            if self.entity_description.data_type == ModbusDataType.COIL:
                value = True
            elif self.entity_description.data_type == ModbusDataType.HOLDING_REGISTER:
                value = self.entity_description.on
            else:
                raise ValueError("Invalid data_type for switch")
            await self.coordinator.client.write_data(self.coordinator_context, value)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        raise NotImplementedError()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if isinstance(self.coordinator, ModbusCoordinator) and isinstance(
            self.entity_description, ModbusSwitchEntityDescription
        ):
            if self.entity_description.data_type == ModbusDataType.COIL:
                value = False
            elif self.entity_description.data_type == ModbusDataType.HOLDING_REGISTER:
                value = self.entity_description.off
            else:
                raise ValueError("Invalid data_type for switch")
            await self.coordinator.client.write_data(self.coordinator_context, value)
