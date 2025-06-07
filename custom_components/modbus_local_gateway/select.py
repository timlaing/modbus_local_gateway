"""Modbus Local Gateway selects"""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusSelectEntityDescription
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
        control=ControlType.SELECT,
        entity_class=ModbusSelectEntity,
    )


class ModbusSelectEntity(ModbusCoordinatorEntity, SelectEntity):  # type: ignore
    """Select entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput Select."""
        super().__init__(coordinator, ctx=ctx, device=device)
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
                isinstance(self.entity_description, ModbusSelectEntityDescription)
                and value is not None
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
            super()._handle_coordinator_update()

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
            await self.write_data(value)
