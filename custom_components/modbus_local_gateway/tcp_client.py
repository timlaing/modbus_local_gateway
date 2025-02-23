"""Tcp Client for Modbus Local Gateway integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from .context import ModbusContext

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AsyncModbusTcpClientGateway(AsyncModbusTcpClient):
    """Batches requests based on slave"""

    _CLIENT: dict[str, AsyncModbusTcpClientGateway] = {}

    def __init__(
        self,
        host: str,
        port: int = 502,
        framer: FramerType = FramerType.SOCKET,
        source_address: tuple[str, int] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            host=host,
            port=port,
            framer=framer,
            source_address=source_address,
            **kwargs,
        )
        self.lock = asyncio.Lock()

    async def read_registers(
        self, func, address, count, slave, max_read_size
    ) -> ModbusPDU | None:
        """Helper function for reading and combining registers"""
        modbus_response: ModbusPDU | None = None
        remaining_registers: int = count
        address_to_read: int = address

        while remaining_registers > 0:
            read_count: int = (
                max_read_size
                if remaining_registers > max_read_size
                else remaining_registers
            )

            modbus_response_temp: ModbusPDU = await func(
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

    async def write_holding_registers(
        self, value: list[int] | int, entity: ModbusContext
    ) -> ModbusPDU:
        """Updates the value of an entity"""
        _LOGGER.debug(
            "Writing slave: %d, register (%s): %d, %d",
            entity.slave_id,
            entity.desc.key,
            entity.desc.register_address,
            entity.desc.register_count,
        )

        if isinstance(value, int):
            registers: list[int] = [value]
        else:
            registers = value

        if isinstance(registers, list) and len(registers) == entity.desc.register_count:

            return await super().write_registers(
                entity.desc.register_address,
                registers,  # type: ignore
                slave=entity.slave_id,
            )
        else:
            raise ModbusException("Incorrect number of registers")

    async def update_slave(
        self, entities: list[ModbusContext], max_read_size: int
    ) -> dict[str, ModbusPDU]:
        """Retrieves all values for a single slave"""
        data: dict[str, ModbusPDU] = {}
        async with self.lock:
            await self.connect()
            if not self.connected:
                _LOGGER.warning("Failed to connect to gateway - %s", self)
                return data

            entity: ModbusContext
            for idx, entity in enumerate(entities):
                try:
                    _LOGGER.debug(
                        "Reading slave: %d, register (%s): %d, %d",
                        entity.slave_id,
                        entity.desc.key,
                        entity.desc.register_address,
                        entity.desc.register_count,
                    )

                    modbus_response: ModbusPDU | None = await self.read_registers(
                        func=(
                            self.read_holding_registers
                            if entity.desc.holding_register
                            else self.read_input_registers
                        ),
                        address=entity.desc.register_address,
                        count=entity.desc.register_count,
                        slave=entity.slave_id,
                        max_read_size=max_read_size,
                    )
                    resp_class: type[ModbusPDU] = (
                        ReadHoldingRegistersResponse
                        if entity.desc.holding_register
                        else ReadInputRegistersResponse
                    )

                    if (
                        modbus_response
                        and isinstance(modbus_response, resp_class)
                        and len(modbus_response.registers) == entity.desc.register_count
                    ):
                        data[entity.desc.key] = modbus_response

                except (ModbusException, TimeoutError):
                    if idx == 0:
                        _LOGGER.warning(
                            "Closing connection - Device not available %s [%d]",
                            self,
                            entity.slave_id,
                        )
                        return data

                    _LOGGER.debug(
                        "Unable to retrieve value for slave %d, register (%s): %d, %d",
                        entity.slave_id,
                        entity.desc.key,
                        entity.desc.register_address,
                        entity.desc.register_count,
                    )

            _LOGGER.debug("Closing connection - Update completed %s", self)

        return data

    @classmethod
    def async_get_client_connection(
        cls,
        host: str,
        port: int,
    ) -> AsyncModbusTcpClientGateway:
        """Gets a modbus client object"""
        key: str = f"{host}:{port}"
        if key not in cls._CLIENT:
            _LOGGER.debug("Connecting to gateway %s", key)

            cls._CLIENT[key] = AsyncModbusTcpClientGateway(
                host=host,
                port=port,
                framer=FramerType.SOCKET,
                timeout=1.5,
                retries=5,
            )

        return cls._CLIENT[key]
