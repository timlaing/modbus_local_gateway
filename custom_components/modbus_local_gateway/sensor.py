"""Modbus Local Gateway sensors"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.components.sensor import RestoreSensor
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_FILENAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PREFIX, CONF_SLAVE_ID, DOMAIN
from .coordinator import ModbusContext, ModbusCoordinator
from .helpers import get_gateway_key
from .sensor_types.base import ModbusSensorEntityDescription
from .sensor_types.modbus_device_info import ModbusDeviceInfo

_LOGGER = logging.getLogger(__name__)


def get_prefix(config: dict[str, Any]) -> str:
    """Gets the sensor entity id prefix"""
    prefix = config.get(CONF_PREFIX, "")
    if prefix != "":
        return f"{prefix}-"
    return prefix


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway sensor."""
    config: dict[str, Any] = {**config_entry.data}
    _LOGGER.debug(config)
    coordinator: ModbusCoordinator = hass.data[DOMAIN][get_gateway_key(config_entry)]
    device_info: ModbusDeviceInfo = ModbusDeviceInfo(config[CONF_FILENAME])

    coordinator.max_read_size = device_info.max_read_size

    identifiers = {
        (DOMAIN, f"{coordinator.gateway}-{config[CONF_SLAVE_ID]}"),
    }

    device = DeviceInfo(
        identifiers=identifiers,
        name=f"{get_prefix(config)}{device_info.model}",
        manufacturer=device_info.manufacturer,
        model=device_info.model,
        via_device=list(coordinator.gateway_device.identifiers)[0],
    )

    _LOGGER.debug(device)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [
            ModbusSensorEntity(
                coordinator=coordinator,
                ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID], desc=desc),
                device=device,
            )
            for desc in device_info.entity_desciptions
        ]
        + [
            ModbusSensorEntity(
                coordinator=coordinator,
                ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID], desc=desc),
                device=device,
            )
            for desc in device_info.properties
        ],
        update_before_add=False,
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
        await self.async_get_last_state()
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
