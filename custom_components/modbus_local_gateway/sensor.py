"""Modbus Local Gateway sensors"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from homeassistant.components.sensor import RestoreSensor, SensorExtraStoredData
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ModbusContext, ModbusCoordinator, ModbusCoordinatorEntity
from .entity_management.base import ModbusSensorEntityDescription
from .entity_management.const import ControlType
from .helpers import async_setup_entities

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway sensor."""
    await async_setup_entities(
        hass=hass,
        config_entry=config_entry,
        async_add_entities=async_add_entities,
        control=ControlType.SENSOR,
        entity_class=ModbusSensorEntity,
    )


class ModbusSensorEntity(ModbusCoordinatorEntity, RestoreSensor):  # type: ignore
    """Sensor entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput sensor."""
        super().__init__(coordinator, ctx=ctx, device=device)
        self._attr_native_state: State | None

    async def async_added_to_hass(self) -> None:
        """Restore the state when sensor is added."""
        await super().async_added_to_hass()
        self._attr_native_state = await self.async_get_last_state()
        last_data: (
            SensorExtraStoredData | None
        ) = await self.async_get_last_sensor_data()
        if last_data:
            _LOGGER.debug("%s", last_data)
            self._attr_native_unit_of_measurement = last_data.native_unit_of_measurement
            self._attr_native_value = last_data.native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value: str | int | float | None = cast(
                ModbusCoordinator, self.coordinator
            ).get_data(self.coordinator_context)
            if value is not None and isinstance(
                self.entity_description, ModbusSensorEntityDescription
            ):
                if self._attr_native_value == value:
                    _LOGGER.debug(
                        "Ignoring device value with %s as %s - already set",
                        self.entity_description.key,
                        value,
                    )
                    return

                if (
                    isinstance(self._attr_native_value, float)
                    and isinstance(value, float)
                ) or (
                    isinstance(self._attr_native_value, int) and isinstance(value, int)
                ):
                    if (
                        self.entity_description.max_change
                        and self._attr_native_value - value
                        > self.entity_description.max_change
                    ):
                        _LOGGER.warning(
                            "Ignoring device value with %s as %s - max_change %s",
                            self.entity_description.key,
                            value,
                            self._attr_native_value,
                        )
                        return

                    if (
                        self.state_class == SensorStateClass.TOTAL_INCREASING
                        and self._attr_native_value > value  # type: ignore
                    ):
                        if self.entity_description.never_resets:
                            _LOGGER.warning(
                                "Ignoring device value with %s as %s - never resets %s",
                                self.entity_description.key,
                                value,
                                self._attr_native_value,
                            )

                self._attr_native_value = value
                self.async_write_ha_state()
                _LOGGER.debug(
                    "Updating device with %s as %s",
                    self.entity_description.key,
                    value,
                )

                if (
                    self._attr_device_info
                    and "identifiers" in self._attr_device_info
                    and self.entity_description.key
                    in [
                        "hw_version",
                        "sw_version",
                    ]
                ):
                    attr: dict[str, str] = {self.entity_description.key: str(value)}
                    device_registry: dr.DeviceRegistry = dr.async_get(self.hass)
                    device: dr.DeviceEntry | None = device_registry.async_get_device(
                        self._attr_device_info["identifiers"]
                    )
                    if device:
                        device_registry.async_update_device(
                            device_id=device.id,
                            **attr,  # type: ignore
                        )

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    @property
    def native_value(self) -> float | str | int | None | date | datetime | Decimal:  # type: ignore
        """Return the state of the sensor."""
        result: str | int | float | None | date | datetime | Decimal = (
            super().native_value
        )
        if (
            isinstance(self.entity_description, ModbusSensorEntityDescription)
            and self.entity_description.precision is not None
            and result
            and isinstance(result, float)
        ):
            result = round(result, self.entity_description.precision)
        return result
