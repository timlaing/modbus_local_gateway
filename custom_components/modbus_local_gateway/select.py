"""Modbus Local Gateway selects"""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import async_setup_entities
from .sensor_types.base import (
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
)
from .sensor_types.const import ControlType
from .sensor_types.conversion import Conversion

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
        control=ControlType.SELECT,
        entity_class=ModbusSelectEntity,
    )


class ModbusSelectEntity(CoordinatorEntity, SelectEntity):
    """Select entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput Select."""
        super().__init__(coordinator, context=ctx)
        self._attr_unique_id: str | None = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo | None = device
        if (
            isinstance(ctx.desc, ModbusSelectEntityDescription)
            and ctx.desc.select_options
        ):
            self._attr_options: list[str] = list(ctx.desc.select_options.values())
        self._attr_current_option = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if (
                value is not None
                and isinstance(self.entity_description, ModbusSelectEntityDescription)
                and self.entity_description.select_options
            ):
                self._attr_current_option = self.entity_description.select_options[
                    int(value)
                ]
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    self._attr_current_option,
                )
                self.async_write_ha_state()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        raise NotImplementedError()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if (
            isinstance(self.coordinator, ModbusCoordinator)
            and isinstance(self.entity_description, ModbusSelectEntityDescription)
            and self.entity_description.select_options
        ):
            value: int = list(self.entity_description.select_options.keys())[
                list(self.entity_description.select_options.values()).index(option)
            ]
            registers: list[int] | int = Conversion(
                self.coordinator.client
            ).convert_to_registers(
                value=value,
                desc=cast(ModbusSensorEntityDescription, self.entity_description),
            )

            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=registers
            )
