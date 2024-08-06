"""Modbus Local Gateway number control"""

from __future__ import annotations
from typing import cast


import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import async_setup_entities
from .sensor_types.base import (
    ModbusSensorEntityDescription,
    ModbusNumberEntityDescription,
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
        control=ControlType.NUMBER,
        entity_class=ModbusNumberEntity,
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
        self._attr_unique_id: str | None = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo | None = device
        if isinstance(ctx.desc, ModbusNumberEntityDescription):
            self._attr_native_max_value = ctx.desc.max
            self._attr_native_min_value = ctx.desc.min
        self._attr_mode = NumberMode.BOX

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if value is not None:
                self._attr_native_value = float(value)
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )
                self.async_write_ha_state()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_native_value(self, value: float) -> None:
        """Set new value."""
        raise NotImplementedError()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if isinstance(self.coordinator, ModbusCoordinator):
            registers: list[int] | int = Conversion(
                self.coordinator.client
            ).convert_to_registers(
                value=value,
                desc=cast(ModbusSensorEntityDescription, self.entity_description),
            )

            await self.coordinator.client.write_holding_registers(
                entity=self.coordinator_context, value=registers
            )
