"""Modbus Local Gateway number control"""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusNumberEntityDescription
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
        control=ControlType.NUMBER,
        entity_class=ModbusNumberEntity,
    )


class ModbusNumberEntity(ModbusCoordinatorEntity, NumberEntity):  # type: ignore
    """Number entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput number."""
        super().__init__(coordinator, ctx=ctx, device=device)
        if isinstance(ctx.desc, ModbusNumberEntityDescription):
            self._attr_native_max_value = ctx.desc.max
            self._attr_native_min_value = ctx.desc.min
            self._attr_native_step = (
                ctx.desc.native_step
                if ctx.desc.native_step is not None
                else (
                    ctx.desc.conv_multiplier
                    if ctx.desc.conv_multiplier is not None
                    else 1.0
                )
            )
        else:
            raise TypeError()
        self._attr_mode = (
            ctx.desc.mode
            if isinstance(ctx.desc, ModbusNumberEntityDescription)
            and ctx.desc.mode is not None
            else NumberMode.BOX
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
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
            await self.coordinator.client.write_data(self.coordinator_context, value)

    def _set_state(self, value: float) -> None:
        """Sets the underlying state of the entity,
        formatted based on precision or else conv_multiplier."""
        precision: int | float | None = self.coordinator_context.desc.precision
        multiplier: int | float | None = self.coordinator_context.desc.conv_multiplier

        keep_float: bool = (precision is not None and precision > 0) or (
            precision is None and multiplier is not None and multiplier % 1 != 0
        )

        self._attr_native_value = value if keep_float else int(round(value))
