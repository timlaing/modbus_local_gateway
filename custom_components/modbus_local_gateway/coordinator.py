"""Representation of Modbus Gateway"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pymodbus.pdu import ModbusResponse

from .context import ModbusContext
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER = logging.getLogger(__name__)


class ModbusCoordinator(DataUpdateCoordinator):
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
        self._gateway_device = gateway_device

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Modbus Coordinator - {self._gateway}",
            update_interval=timedelta(seconds=update_interval),
        )

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
    def max_read_size(self, value: int):
        """Sets the max register read size"""
        self._max_read_size = value

    async def _async_refresh(
        self,
        log_failures: bool = False,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ):
        return await super()._async_refresh(
            log_failures, raise_on_auth_failed, scheduled, raise_on_entry_error
        )

    async def _async_update_data(self):
        """Updated all values for devices"""
        entities: list[ModbusContext] = sorted(
            self.async_contexts(), key=lambda x: x.slave_id
        )
        return await self._update_device(entities=entities)

    async def _update_device(self, entities: list[ModbusContext]) -> dict[str, Any]:
        _LOGGER.debug("Updating data for %s (%s)", self.name, self.client)
        resp: dict[str, ModbusResponse] = await self.client.update_slave(
            entities, max_read_size=self._max_read_size
        )
        data: dict[str, Any] = {}

        entity: ModbusContext
        for entity in entities:
            if entity.desc.key in resp:
                modbus_response: ModbusResponse = resp[entity.desc.key]
                value = self.translate_data(ctx=entity, response=modbus_response)
                data[entity.desc.key] = value
                _LOGGER.debug("Value for key %s is %s", entity.desc.key, value)

        return data

    def get_data(self, ctx: ModbusContext) -> str | int | None:
        """returns the pre-retrieved data"""
        if self.data and ctx.desc.key in self.data:
            return self.data[ctx.desc.key]

    def translate_data(
        self, ctx: ModbusContext, response: ModbusResponse
    ) -> str | int | None:
        """returns the value of the registers"""
        try:
            if ctx.desc.string:
                value: str = self.client.convert_from_registers(
                    response.registers, data_type=self.client.DATATYPE.STRING
                ).split("\0")[0]
                return value
            if ctx.desc.float:
                value: float = self.client.convert_from_registers(
                    response.registers, data_type=self.client.DATATYPE.FLOAT32
                )
                return value

            if ctx.desc.register_map:
                value: int = ctx.desc.register_map[response.registers[0]]

                return value

            num = self.client.convert_from_registers(
                response.registers,
                data_type=self.client.DATATYPE.INT32
                if ctx.desc.register_count == 2
                else self.client.DATATYPE.INT16,
            )

            return num * ctx.desc.register_multiplier
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.debug(
                "Data not available for key: %s (%d)", ctx.desc.key, ctx.slave_id
            )
