"""Tcp Client for Modbus Local Gateway integration."""
from __future__ import annotations

import logging
import asyncio
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Defaults
from pymodbus.framer import ModbusFramer
from pymodbus.framer.socket_framer import ModbusSocketFramer
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ModbusResponse

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT

from .context import ModbusContext


_LOGGER = logging.getLogger(__name__)


class AsyncModbusTcpClientGateway(AsyncModbusTcpClient):
    """Batches requests based on slave"""

    _CLIENT: dict[str, AsyncModbusTcpClientGateway] = {}

    def __init__(self, host: str, port: int = Defaults.TcpPort, framer: type[ModbusFramer] = ModbusSocketFramer, source_address: tuple[str, int] = None, **kwargs: Any) -> None:
        super().__init__(host, port, framer, source_address, **kwargs)
        self.lock = asyncio.Lock()

    async def read_registers(self, func, address, count, slave, max_read_size):
        """Helper function for reading and combining registers"""
        modbus_response: ModbusResponse = None
        remaining_registers: int = count
        address_to_read: int = address

        while remaining_registers > 0:
            read_count: int = max_read_size if remaining_registers > max_read_size else remaining_registers

            modbus_response_temp: ModbusResponse = await func(
                address=address_to_read,
                count=read_count,
                slave=slave,
            )

            remaining_registers -= read_count
            address_to_read += read_count

            if modbus_response is None:
                modbus_response = modbus_response_temp
            else:
                _LOGGER.debug("Appending registers to existing response")
                modbus_response.registers += modbus_response_temp.registers

        return modbus_response

    async def update_slave(self, entities: list[ModbusContext], max_read_size: int) -> dict[str, ModbusResponse]:
        """Retrieves all values for a single slave"""
        data: dict[str, ModbusResponse] = {}
        async with self.lock:

            await self.connect()
            if not self.connected:
                raise ConnectionException(f"Failed to connect to gateway - {self}")

            entity: ModbusContext
            for entity in entities:
                try:
                    _LOGGER.debug("Reading slave: %d, register (%s): %d, %d", entity.slave_id, entity.desc.key, entity.desc.register_address, entity.desc.register_count)
                    if entity.slave_id not in data:
                        data[entity.slave_id] = {}

                    modbus_response: ModbusResponse = await self.read_registers(
                        func=self.read_holding_registers if entity.desc.holding_register else self.read_input_registers,
                        address=entity.desc.register_address,
                        count=entity.desc.register_count,
                        slave=entity.slave_id,
                        max_read_size=max_read_size,
                    )

                    data[entity.desc.key] = modbus_response

                except (ModbusException, asyncio.TimeoutError):
                    _LOGGER.warning("Unable to retrieve value for slave %d, register (%s): %d, %d", entity.slave_id, entity.desc.key, entity.desc.register_address, entity.desc.register_count)
                    await asyncio.sleep(1)

            _LOGGER.debug("Closing connection - Update completed %s", self)

        return data


    @classmethod
    async def async_get_client_connection(cls:AsyncModbusTcpClientGateway, hass: HomeAssistant, data: dict[str, Any]):
        """Gets a modbus client object"""
        key = f"{data[CONF_HOST]}:{data[CONF_PORT]}"
        if key not in cls._CLIENT:
            _LOGGER.debug("Connecting to gateway %s", key)

            cls._CLIENT[key] = AsyncModbusTcpClientGateway(
                host=data[CONF_HOST],
                port=data[CONF_PORT],
                framer=ModbusSocketFramer,
                timeout=0.5,
                RetryOnEmpty=True,
                RetryOnInvalid=True,
                Retries=5,
                Reconnects=3,
                IgnoreMissingSlaves=True,
            )

        return cls._CLIENT[key]
