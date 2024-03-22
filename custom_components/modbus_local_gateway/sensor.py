"""Modbus Local Gateway sensors"""

from __future__ import annotations

import datetime
import logging

from homeassistant.components.sensor import RestoreSensor, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import async_setup_entities
from .sensor_types.base import ModbusSensorEntityDescription
from .sensor_types.const import ControlType

_LOGGER = logging.getLogger(__name__)


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


class ModbusSensorEntity(CoordinatorEntity, RestoreSensor):
    """Sensor entity for Modbus gateway"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize a PVOutput sensor."""
        super().__init__(coordinator, context=ctx)
        self.entity_description: ModbusSensorEntityDescription = ctx.desc
        self._attr_unique_id: str = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo = device

    async def async_added_to_hass(self) -> None:
        """Restore the state when sensor is added."""
        await super().async_added_to_hass()
        self._attr_state = await self.async_get_last_state()
        await self.async_get_last_sensor_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_data(self.coordinator_context)
            if value is not None:
                if (
                    self.native_value is not None
                    and self.state_class == SensorStateClass.TOTAL_INCREASING
                    and self.native_value > value
                ):
                    if self.entity_description.never_resets:
                        return

                    self.last_reset = datetime.datetime.now()

                self._attr_native_value = value
                self.async_write_ha_state()

                if self.entity_description.key in ["hw_version", "sw_version"]:
                    attr: dict[str, str] = {self.entity_description.key: value}
                    _LOGGER.debug(
                        "Updating device with %s as %s",
                        self.entity_description.key,
                        value,
                    )
                    device_registry = dr.async_get(self.hass)
                    device = device_registry.async_get_device(
                        self._attr_device_info["identifiers"]
                    )
                    device_registry.async_update_device(device_id=device.id, **attr)

        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        result = super().native_value
        if self.entity_description.precision is not None and result:
            result = round(result, self.entity_description.precision)
        return result
