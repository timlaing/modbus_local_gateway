"""Modbus Local Gateway number control"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusNumberEntityDescription
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
        control=ControlType.NUMBER,
        entity_class=ModbusNumberEntity,
    )


class ModbusNumberEntity(ModbusCoordinatorEntity, NumberEntity):
    """Number entity for Modbus gateway"""

    entity_description: ModbusNumberEntityDescription

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput number."""
        super().__init__(coordinator, ctx=ctx, device=device)
        if not isinstance(ctx.desc, ModbusNumberEntityDescription):
            raise TypeError()

        self._attr_native_max_value = ctx.desc.max
        self._attr_native_min_value = ctx.desc.min
        # The step of an entity is what one press of the control changes: a
        # conversion multiplier says how much the register is worth, which is
        # the step unless the config asks for one of its own.
        step: float = 1.0
        if ctx.desc.native_step is not None:
            step = float(ctx.desc.native_step)
        elif ctx.desc.conv_multiplier is not None:
            step = float(ctx.desc.conv_multiplier)
        else:
            step = 1.0
        self._attr_native_step = step
        self._attr_mode = ctx.desc.mode or NumberMode.BOX

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | float | None = self.coordinator.get_data(
                self.coordinator_context
            )
            if value is not None:
                self._set_state(float(value))
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )
            super()._handle_coordinator_update()

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    def set_native_value(self, value: float) -> None:
        """Set new value."""
        raise NotImplementedError()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if isinstance(self.coordinator, ModbusCoordinator):
            await self.write_data(value)

    def _set_state(self, value: float) -> None:
        """Sets the underlying state of the entity,
        formatted based on precision or else conv_multiplier."""
        precision: int | float | None = self.coordinator_context.desc.precision
        multiplier: int | float | None = self.coordinator_context.desc.conv_multiplier

        keep_float: bool = (precision is not None and precision > 0) or (
            precision is None and multiplier is not None and multiplier % 1 != 0
        )

        self._attr_native_value = value if keep_float else round(value)
