"""Modbus Local Gateway sensors"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import CONF_FILENAME
from homeassistant.helpers import device_registry as dr


from .const import DOMAIN, CONF_SLAVE_ID
from .sensor_types.base import ModbusSensorEntityDescription
from .sensor_types.modbus_device_info import ModbusDeviceInfo
from .coordinator import ModbusCoordinator, ModbusContext
from .helpers import get_gateway_key

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Local Gateway sensor."""
    config = {**config_entry.data}
    _LOGGER.debug(config)
    coordinator: ModbusCoordinator = hass.data[DOMAIN][get_gateway_key(config_entry)]
    device_info:ModbusDeviceInfo = ModbusDeviceInfo(config[CONF_FILENAME])

    coordinator.max_read_size = device_info.max_read_size

    identifiers = {
        (DOMAIN, f"{coordinator.gateway}-{config[CONF_SLAVE_ID]}"),
    }

    device = DeviceInfo(
            identifiers=identifiers,
            default_name=device_info.model,
            manufacturer=device_info.manufacturer,
            model=device_info.model,
            via_device=list(coordinator.gateway_device.identifiers)[0],
    )

    _LOGGER.debug(device)

    async_add_entities(
        [ModbusSensorEntity(coordinator=coordinator,
                            ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID],
                                              desc=desc),
                            device=device) for desc in device_info.entity_desciptions],
        update_before_add=True
    )
    async_add_entities(
        [ModbusSensorEntity(coordinator=coordinator,
                            ctx=ModbusContext(slave_id=config[CONF_SLAVE_ID],
                                              desc=desc),
                            device=device) for desc in device_info.properties],
        update_before_add=True
    )


class ModbusSensorEntity(CoordinatorEntity, SensorEntity):
    """Sensor entity for Modbus gateway"""

    def __init__(self, coordinator: ModbusCoordinator, ctx: ModbusContext, device: DeviceInfo) -> None:
        """Initialize a PVOutput sensor."""
        super().__init__(coordinator, context=ctx)
        self.entity_description: ModbusSensorEntityDescription = ctx.desc
        self._attr_unique_id = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info = device


    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        try:
            value = self.coordinator.get_data(self.coordinator_context)
            if value is not None:
                self._attr_native_value = value
                self.async_write_ha_state()

                if self.entity_description.key in ["hw_version", "sw_version"]:
                    attr: dict[str, str] = {self.entity_description.key: value}
                    _LOGGER.debug("Updating device with %s as %s",
                                  self.entity_description.key, value)
                    device_registry = dr.async_get(self.hass)
                    device = device_registry.async_get_device(self._attr_device_info["identifiers"])
                    device_registry.async_update_device(device_id=device.id, **attr)

        except Exception as err: # pylint: disable=broad-exception-caught
            _LOGGER.error("Unable to get data for %s %s", self.name, err)


    @property
    def native_value(self):
        """Return the state of the sensor."""
        result = super().native_value
        if self.entity_description.precision is not None and result:
            result = round(result, self.entity_description.precision)
        return result
