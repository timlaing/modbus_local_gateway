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


class SameValue(Exception):
    """Exception raised when the value is the same as the previous value."""

    def __init__(
        self, desc: ModbusSensorEntityDescription, value: str | int | float
    ) -> None:
        """Initialize the exception."""
        super().__init__("Ignoring device value - same as previous value.")
        self.desc: ModbusSensorEntityDescription = desc
        self.value: str | int | float = value


class MaxChangeExceeded(Exception):
    """Exception raised when the change in value exceeds the maximum allowed change."""

    def __init__(
        self,
        desc: ModbusSensorEntityDescription,
        value: int | float,
        prev_value: int | float,
    ) -> None:
        """Initialize the exception."""
        super().__init__("Change in value exceeds maximum allowed change.")
        self.desc: ModbusSensorEntityDescription = desc
        self.value: int | float = value
        self.prev_value: int | float = prev_value


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
        self._first_update_received: bool = False
        self.entity_description: ModbusSensorEntityDescription

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
            if value is not None:
                self._validate_and_update_value(value)
                self._update_device_versions(value)
        except SameValue as err:
            _LOGGER.debug(
                "Ignoring device value for %s: %s – same as previous value",
                err.desc.key,
                err.value,
            )
        except MaxChangeExceeded as err:
            _LOGGER.warning(
                "Ignoring device value for %s: %s – change Δ=%s exceeds max_change=%s",
                err.desc.key,
                err.value,
                abs(err.value - err.prev_value),
                err.desc.max_change,
            )
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

        super()._handle_coordinator_update()

    def _validate_and_update_value(self, value: str | int | float) -> None:
        """Validate the value and update the state."""
        if self._attr_native_value == value:
            raise SameValue(self.entity_description, value)
        if (
            isinstance(self._attr_native_value, float) and isinstance(value, float)
        ) or (isinstance(self._attr_native_value, int) and isinstance(value, int)):
            if self._round_value(self._attr_native_value) == self._round_value(value):
                raise SameValue(self.entity_description, value)
            if (
                self.entity_description.max_change is not None
                and abs(
                    self._round_value(value)
                    - self._round_value(self._attr_native_value)
                )
                > self.entity_description.max_change
                and self._first_update_received
            ):
                raise MaxChangeExceeded(
                    self.entity_description,
                    value,
                    self._attr_native_value,
                )

            if (
                self.state_class == SensorStateClass.TOTAL_INCREASING
                and int(self._attr_native_value) > int(value)
                and self.entity_description.never_resets
            ):
                _LOGGER.warning(
                    "Ignoring device value with %s as %s - never resets %s",
                    self.entity_description.key,
                    value,
                    self._attr_native_value,
                )

        self._attr_native_value = value
        self._first_update_received = True

        _LOGGER.debug(
            "Updating device with %s as %s",
            self.entity_description.key,
            value,
        )

    def _update_device_versions(self, value: str | int | float) -> None:
        """Update device registry for version keys."""
        if (
            self._attr_device_info
            and "identifiers" in self._attr_device_info
            and self.entity_description.key
            in [
                "hw_version",
                "sw_version",
            ]
        ):
            device_registry: dr.DeviceRegistry = dr.async_get(self.hass)
            device: dr.DeviceEntry | None = device_registry.async_get_device(
                self._attr_device_info["identifiers"]
            )
            if device:
                if self.entity_description.key == "hw_version":
                    device_registry.async_update_device(
                        device_id=device.id,
                        hw_version=str(value),
                    )
                elif self.entity_description.key == "sw_version":
                    device_registry.async_update_device(
                        device_id=device.id,
                        sw_version=str(value),
                    )

    def _round_value(self, value: float | int) -> float | int:
        """Round the value based on the entity description precision."""
        if (
            isinstance(self.entity_description, ModbusSensorEntityDescription)
            and self.entity_description.precision is not None
            and isinstance(value, float)
        ):
            return round(value, self.entity_description.precision)
        return value

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
            result = self._round_value(result)
        return result
