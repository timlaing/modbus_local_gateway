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
        """Execute the precomputed read plan and return responses"""
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
                    response = await self.read_data(
                        func=func,
                        address=start,
                        count=count,
                        slave=slave,
                        max_read_size=max_read_size,
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

    async def read_data(self, func: callable, address: int, count: int, slave: int, max_read_size: int) -> ModbusPDU | None:
        """Read registers or coils in batches based on max_read_size"""
        is_register_func = func in [self.read_holding_registers, self.read_input_registers]
        response: ModbusPDU | None = None
        remaining: int = count
        current_address: int = address

        _LOGGER.debug(
            "Trying to read %d registers/coils from address %d",
            count,
            address,
        )

        while remaining > 0:
            read_count: int = min(max_read_size, remaining)
            temp_response: ModbusPDU = await func(
                address=current_address,
                count=read_count,
                slave=slave,
            )

            if not hasattr(temp_response, "registers" if is_register_func else "bits"):
                _LOGGER.error("Invalid response received from slave %d", slave)
                return None

            remaining -= read_count
            current_address += read_count

            if response is None:
                response = temp_response
            else:
                if is_register_func:
                    _LOGGER.debug(
                        "Appending %d registers from address %d",
                        len(temp_response.registers),
                        current_address - read_count,
                    )
                    response.registers += temp_response.registers
                else:  # Coils or discrete inputs
                    _LOGGER.debug(
                        "Appending %d bits from address %d",
                        len(temp_response.bits),
                        current_address - read_count,
                    )
                    response.bits += temp_response.bits

        return response

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

    async def update_slave(self, entities: list[ModbusContext], max_read_size: int) -> dict[str, ModbusPDU]:
        data: dict[str, ModbusPDU] = {}
        async with self.lock:
            # Ensure connection before proceeding
            if not self.connected:
                await self.connect()
                if not self.connected:
                    _LOGGER.warning("Failed to connect to gateway - %s", self)
                    return data  # Return empty data if connection fails

            # Process each entity individually
            for entity in entities:
                _LOGGER.debug(
                    "Reading slave: %d, register/coil (%s): %d, count: %d",
                    entity.slave_id,
                    entity.desc.key,
                    entity.desc.register_address,
                    entity.desc.register_count,
                )
                func = self._DATA_TYPE_TO_FUNC.get(entity.desc.data_type)
                if func is None:
                    _LOGGER.error("Invalid data type: %s", entity.desc.data_type)
                    continue

                try:
                    modbus_response = await self.read_data(
                        func=func,
                        address=entity.desc.register_address,
                        count=entity.desc.register_count * (len(entity.desc.sum_scale) if entity.desc.sum_scale is not None else 1),
                        slave=entity.slave_id,
                        max_read_size=max_read_size,
                    )

                    # Check if the response is valid and not an error
                    if modbus_response and not modbus_response.isError():
                        data[entity.desc.key] = modbus_response
                    else:
                        _LOGGER.debug("Error reading %s: %s", entity.desc.key, modbus_response)
                except (ModbusException, TimeoutError) as e:
                    _LOGGER.debug(
                        "Unable to retrieve value for slave %d, register/coil (%s): %s",
                        entity.slave_id,
                        entity.desc.key,
                        str(e)
                    )

            _LOGGER.debug("Update completed %s", self)
        return data

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
