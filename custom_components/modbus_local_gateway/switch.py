"""Modbus Local Gateway switches"""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusCoordinator, ModbusCoordinatorEntity
from .helpers import async_setup_entities
from .sensor_types.base import ModbusSwitchEntityDescription
from .sensor_types.const import ControlType

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


class ModbusSwitchEntity(ModbusCoordinatorEntity, SwitchEntity):  # type: ignore
    """Switch entity for Modbus gateway"""

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if value is not None and isinstance(
                self.entity_description, ModbusSwitchEntityDescription
            ):
                self._attr_is_on = value == self.entity_description.on
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
            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=self.entity_description.on
            )

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        raise NotImplementedError()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        if isinstance(self.coordinator, ModbusCoordinator) and isinstance(
            self.entity_description, ModbusSwitchEntityDescription
        ):
            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=self.entity_description.off
            )
