"""Representation of Modbus Gateway"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
)
from pymodbus.pdu.pdu import ModbusPDU

from .context import ModbusContext
from .sensor_types.base import ModbusEntityDescription
from .sensor_types.conversion import Conversion
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)


class ModbusCoordinatorEntity(CoordinatorEntity):
    """Base class for Modbus Entities"""

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize an entity."""
        super().__init__(coordinator, context=ctx)
        if isinstance(ctx.desc, ModbusEntityDescription):
            self.entity_description = ctx.desc
        else:
            raise TypeError()
        self._attr_unique_id: str | None = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo | None = device


class ModbusCoordinator(TimestampDataUpdateCoordinator):
    """Update coordinator for modbus entries"""

    def __init__(
        self,
        hass: HomeAssistant,
        gateway_device: dr.DeviceEntry,
        client: AsyncModbusTcpClientGateway,
        gateway: str,
        update_interval: int = 30,
    ) -> None:
        """Initialise the coordinator"""
        self.client: AsyncModbusTcpClientGateway = client
        self._gateway: str = gateway
        self._max_read_size: int
        self._gateway_device: dr.DeviceEntry = gateway_device
        self.started: bool = hass.is_running

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Modbus Coordinator - {self._gateway}",
            update_interval=timedelta(seconds=update_interval),
            update_method=self.async_update,  # type: ignore
            always_update=False,
        )

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._async_enable_sync)

    async def _async_enable_sync(self, _) -> None:
        """Allow sync of devices after startup"""
        self.started = True

    @property
    def gateway_device(self) -> dr.DeviceEntry:
        """Returns the gateway name"""
        return self._gateway_device

    @property
    def gateway(self) -> str:
        """Returns the gateway name"""
        return self._gateway

    @property
    def max_read_size(self) -> int:
        """Return the current max register read size"""
        return self._max_read_size

    @max_read_size.setter
    def max_read_size(self, value: int) -> None:
        """Sets the max register read size"""
        self._max_read_size = value

    async def _async_refresh(
        self,
        log_failures: bool = False,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ) -> None:
        return await super()._async_refresh(
            log_failures, raise_on_auth_failed, scheduled, raise_on_entry_error
        )

    async def async_update(self) -> dict[str, Any] | None:
        """Updated all values for devices"""
        if self.started:
            entities: list[ModbusContext] = sorted(
                self.async_contexts(), key=lambda x: x.slave_id
            )
            return await self._update_device(entities=entities)

    async def _update_device(self, entities: list[ModbusContext]) -> dict[str, Any]:
        _LOGGER.debug("Updating data for %s (%s)", self.name, self.client)
        resp: dict[str, ModbusPDU] = await self.client.update_slave(
            entities, max_read_size=self._max_read_size
        )
        data: dict[str, Any] = {}
        conversion: Conversion = Conversion(type(self.client))

        entity: ModbusContext
        for entity in entities:
            if entity.desc.key in resp:
                modbus_response: ModbusPDU = resp[entity.desc.key]
                try:
                    value: str | float | int | None = conversion.convert_from_registers(
                        desc=entity.desc, registers=modbus_response.registers
                    )
                    data[entity.desc.key] = value
                    _LOGGER.debug("Value for key %s is %s", entity.desc.key, value)
                except Exception:  # pylint: disable=broad-exception-caught
                    _LOGGER.debug(
                        "Data not available for key: %s (%d)",
                        entity.desc.key,
                        entity.slave_id,
                    )

        return data

    def get_data(self, ctx: ModbusContext) -> str | int | None:
        """returns the pre-retrieved data"""
        if self.data and ctx.desc.key in self.data:
            return self.data[ctx.desc.key]
        return None
