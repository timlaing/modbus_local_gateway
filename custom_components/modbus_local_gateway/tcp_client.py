"""TCP Client for Modbus Local Gateway"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, List, Dict, Tuple

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType
from pymodbus.pdu import ModbusPDU

from .context import ModbusContext
from .entity_management.const import ModbusDataType

_LOGGER: logging.Logger = logging.getLogger(__name__)

class AsyncModbusTcpClientGateway(AsyncModbusTcpClient):
    """Custom Modbus TCP client with request batching based on slave and locking."""

    _CLIENT: dict[str, AsyncModbusTcpClientGateway] = {}

    def __init__(
        self,
        host: str,
        port: int = 502,
        framer: FramerType = FramerType.SOCKET,
        source_address: tuple[str, int] | None = None,
        **kwargs: Any,
    ) -> None:
        self._DATA_TYPE_TO_FUNC: dict[str, callable] = {
            ModbusDataType.HOLDING_REGISTER: self.read_holding_registers,
            ModbusDataType.INPUT_REGISTER: self.read_input_registers,
            ModbusDataType.COIL: self.read_coils,
            ModbusDataType.DISCRETE_INPUT: self.read_discrete_inputs
        }
        super().__init__(host=host, port=port, framer=framer, source_address=source_address, **kwargs)
        self.lock = asyncio.Lock()

    async def batch_read(self, read_plan: Dict[str, List[Tuple[int, int]]], slave: int, max_read_size: int) -> Dict[str, List[ModbusPDU]]:
        """Execute the precomputed read plan and return responses."""
        responses: Dict[str, List[ModbusPDU]] = {}
        async with self.lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    _LOGGER.warning("Failed to connect to gateway - %s", self)
                    return responses

            for category, requests in read_plan.items():
                responses[category] = []
                func = self._DATA_TYPE_TO_FUNC.get(category)
                if func is None:
                    _LOGGER.error("Invalid category: %s", category)
                    continue
                for start, count in requests:
                    _LOGGER.debug(
                        "Reading %s from %d, count %d, slave %d",
                        category, start, count, slave
                    )
                    response = await func(
                        address=start,
                        count=count,
                        slave=slave,
                    )
                    if response and not response.isError():
                        responses[category].append(response)
                    else:
                        _LOGGER.error(
                            "Failed to read %s from %d for %d units",
                            category, start, count
                        )
                        responses[category].append(None)  # Maintain order
        return responses

    async def _custom_write_registers(self, address: int, values: List[int], slave: int) -> None:
        """Write values to Modbus registers. Try write_registers first, and fall back to individual write_register calls if it fails."""
        if len(values) == 0:
            _LOGGER.debug("No values to write, skipping.")
            return

        if len(values) == 1:
            # Single value: use write_register directly
            _LOGGER.debug(f"Writing single value {values[0]} to register at address {address}, slave {slave}")
            result = await self.write_register(address=address, value=values[0], slave=slave)
            if result.isError():
                _LOGGER.error(f"Failed to write value {values[0]} to address {address}: {result}")
            else:
                _LOGGER.debug("Writing successful")
        else:
            # Multiple values: try write_registers first
            _LOGGER.debug(f"Attempting to write multiple values {values} starting at address {address}, slave {slave} using write_registers")
            result = await self.write_registers(address=address, values=values, slave=slave)
            if result.isError():
                _LOGGER.warning(f"Failed to write multiple values using write_registers: {result}. Falling back to old method (individual write_register calls).")
                # Fallback method: individual write_register calls
                for i, value in enumerate(values):
                    current_address = address + i
                    _LOGGER.debug(f"Writing value {value} to register at address {current_address}, slave {slave}")
                    result = await self.write_register(address=current_address, value=value, slave=slave)
                    if result.isError():
                        _LOGGER.error(f"Failed to write value {value} to address {current_address}: {result}")
                        return
                _LOGGER.debug("All individual writes successful using fallback")
            else:
                _LOGGER.debug("Writing multiple values using write_registers successful")

    async def write_data(self, entity: ModbusContext, value: Any) -> ModbusPDU:
        """Writes data to Holding Registers or Coils"""
        async with self.lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    _LOGGER.warning("Failed to connect to gateway - %s", self)
                    return None

            _LOGGER.debug(
                "Starting write operation - Slave: %d, %s (%s): %d, Count: %d",
                entity.slave_id,
                entity.desc.data_type,
                entity.desc.key,
                entity.desc.register_address,
                entity.desc.register_count,
            )
            _LOGGER.debug("Value before conversion: %s (type: %s)", value, type(value).__name__)

            if entity.desc.data_type == ModbusDataType.HOLDING_REGISTER:
                from .conversion import Conversion
                registers = Conversion(type(self)).convert_to_registers(entity.desc, value)
                _LOGGER.debug("Raw value after conversion to registers: %s (type: %s)", registers, type(registers).__name__)
                if len(registers) != entity.desc.register_count:
                    raise ModbusException("Incorrect number of registers: expected %d, got %d", entity.desc.register_count, len(registers))
                return await self._custom_write_registers(
                    address=entity.desc.register_address,
                    values=registers,
                    slave=entity.slave_id,
                )
            elif entity.desc.data_type == ModbusDataType.COIL:
                if not isinstance(value, bool):
                    raise TypeError("Value for COIL must be boolean, got %s", type(value).__name__)
                return await self.write_coil(
                    entity.desc.register_address,
                    value,
                    slave=entity.slave_id,
                )
            else:
                raise ValueError("Unsupported data type: %s", entity.desc.data_type)

    @classmethod
    def async_get_client_connection(cls, host: str, port: int) -> AsyncModbusTcpClientGateway:
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
