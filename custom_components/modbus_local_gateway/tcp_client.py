"""TCP Client for Modbus Local Gateway"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, Callable, List

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.framer import FramerType
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.transaction import TransactionManager

from .context import ModbusContext
from .conversion import Conversion
from .entity_management.const import ModbusDataType

_LOGGER: logging.Logger = logging.getLogger(__name__)


class MyTransactionManager(TransactionManager):
    """Custom Transaction Manager to supress exception logging"""

    def data_received(self, data: bytes) -> None:
        """Catch any protocol exceptions so they don't pollute the HA logs"""
        with contextlib.suppress(ModbusIOException):
            super().data_received(data)


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
        self._data_type_function_mapping: dict[str, Callable] = {
            ModbusDataType.HOLDING_REGISTER: self.read_holding_registers,
            ModbusDataType.INPUT_REGISTER: self.read_input_registers,
            ModbusDataType.COIL: self.read_coils,
            ModbusDataType.DISCRETE_INPUT: self.read_discrete_inputs,
        }
        self.lock = asyncio.Lock()
        super().__init__(
            host=host, port=port, framer=framer, source_address=source_address, **kwargs
        )
        self.ctx = MyTransactionManager(
            params=self.ctx.comm_params,
            framer=self.ctx.framer,
            retries=self.ctx.retries,
            is_server=self.ctx.is_server,
            trace_connect=self.ctx.trace_connect,
            trace_packet=self.ctx.trace_packet,
            trace_pdu=self.ctx.trace_pdu,
        )

    async def read_data(
        self, func: Callable, address: int, count: int, slave: int, max_read_size: int
    ) -> ModbusPDU | None:
        """Read registers or coils in batches based on max_read_size."""
        is_register_func: bool = func in [
            self.read_holding_registers,
            self.read_input_registers,
        ]
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

            if (
                hasattr(temp_response, "registers")
                and len(temp_response.registers) != read_count
            ):
                _LOGGER.error(
                    "Invalid response received from slave %d, address: %d (count does not match)",
                    slave,
                    current_address,
                )
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

    async def _custom_write_registers(
        self, address: int, values: List[int], slave: int
    ) -> None:
        """Write values to Modbus registers. Try write_registers first, and
        fall back to individual write_register calls if it fails."""
        if not values:
            _LOGGER.debug("No values to write, skipping.")
            return

        if len(values) == 1:
            await self._write_single_register(address, values[0], slave)
        else:
            await self._write_multiple_registers(address, values, slave)

    async def _write_single_register(
        self, address: int, value: int, slave: int
    ) -> None:
        """Write a single value to a Modbus register."""
        _LOGGER.debug(
            "Writing single value %d to register at address %d, slave %d",
            value,
            address,
            slave,
        )
        result: ModbusPDU = await self.write_register(
            address=address, value=value, slave=slave
        )
        if result.isError():
            _LOGGER.error(
                "Failed to write value %d to address %d: %s",
                value,
                address,
                result,
            )
        else:
            _LOGGER.debug("Writing successful")

    async def _write_multiple_registers(
        self, address: int, values: List[int], slave: int
    ) -> None:
        """Write multiple values to Modbus registers."""
        _LOGGER.debug(
            "Attempting to write multiple values %s starting at address %d, "
            "slave %d using write_registers",
            values,
            address,
            slave,
        )
        result: ModbusPDU = await self.write_registers(
            address=address, values=values, slave=slave
        )
        if result.isError():
            _LOGGER.warning(
                "Failed to write multiple values using write_registers: %s. "
                "Falling back to old method (individual write_register calls).",
                result,
            )
            await self._write_registers_individually(address, values, slave)
        else:
            _LOGGER.debug("Writing multiple values using write_registers successful")

    async def _write_registers_individually(
        self, address: int, values: List[int], slave: int
    ) -> None:
        """Fallback method to write multiple values to Modbus registers individually."""
        for i, value in enumerate(values):
            current_address = address + i
            _LOGGER.debug(
                "Writing value %d to register at address %d, slave %d",
                value,
                current_address,
                slave,
            )
            result: ModbusPDU = await self.write_register(
                address=current_address, value=value, slave=slave
            )
            if result.isError():
                _LOGGER.error(
                    "Failed to write value %d to address %d: %s",
                    value,
                    current_address,
                    result,
                )
                return
        _LOGGER.debug("All individual writes successful using fallback")

    async def write_data(self, entity: ModbusContext, value: Any) -> ModbusPDU | None:
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
            _LOGGER.debug(
                "Value before conversion: %s (type: %s)", value, type(value).__name__
            )

            if entity.desc.data_type == ModbusDataType.HOLDING_REGISTER:
                registers = Conversion(type(self)).convert_to_registers(
                    entity.desc, value
                )
                _LOGGER.debug(
                    "Raw value after conversion to registers: %s (type: %s)",
                    registers,
                    type(registers).__name__,
                )
                if len(registers) != entity.desc.register_count:
                    raise ModbusException(
                        "Incorrect number of registers: expected "
                        f"{entity.desc.register_count}, got {len(registers)}"
                    )
                return await self._custom_write_registers(
                    address=entity.desc.register_address,
                    values=registers,
                    slave=entity.slave_id,
                )
            elif entity.desc.data_type == ModbusDataType.COIL:
                if not isinstance(value, bool):
                    raise TypeError(
                        f"Value for COIL must be boolean, got {type(value).__name__}"
                    )
                return await self.write_coil(
                    address=entity.desc.register_address,
                    value=value,
                    slave=entity.slave_id,
                )
            else:
                raise ValueError(f"Unsupported data type: {entity.desc.data_type}")

    async def update_slave(
        self, entities: list[ModbusContext], max_read_size: int
    ) -> dict[str, ModbusPDU]:
        """Fetches all values for a single slave"""
        data: dict[str, ModbusPDU] = {}
        async with self.lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    _LOGGER.warning("Failed to connect to gateway - %s", self)
                    return data

            for idx, entity in enumerate(entities):
                await self._process_entity(entity, data, idx, max_read_size)

            _LOGGER.debug("Update completed %s", self)

        return data

    async def _process_entity(
        self,
        entity: ModbusContext,
        data: dict[str, ModbusPDU],
        idx: int,
        max_read_size: int,
    ) -> None:
        """Process a single entity and update the data dictionary"""
        _LOGGER.debug(
            "Reading slave: %d, register/coil (%s): %d, count: %d",
            entity.slave_id,
            entity.desc.key,
            entity.desc.register_address,
            entity.desc.register_count,
        )
        func: Callable | None = self._data_type_function_mapping.get(
            entity.desc.data_type
        )
        if func is None:
            raise ValueError(f"Invalid data type: {entity.desc.data_type}")
        if entity.desc.register_count is None or entity.desc.register_count == 0:
            raise ValueError("Invalid register count")

        try:
            modbus_response: ModbusPDU | None = await self.read_data(
                func=func,
                address=entity.desc.register_address,
                count=entity.desc.register_count
                * (
                    len(entity.desc.sum_scale)
                    if entity.desc.sum_scale is not None
                    else 1
                ),
                slave=entity.slave_id,
                max_read_size=max_read_size,
            )

            if modbus_response and not modbus_response.isError():
                data[entity.desc.key] = modbus_response
            else:
                _LOGGER.debug("Error reading %s", entity.desc.key)

        except (ModbusException, TimeoutError):
            if idx == 0:
                _LOGGER.warning(
                    "Device not available %s [%d]",
                    self,
                    entity.slave_id,
                )
                return
            _LOGGER.debug(
                "Unable to retrieve value for slave %d, register/coil (%s): %d, count: %d",
                entity.slave_id,
                entity.desc.key,
                entity.desc.register_address,
                entity.desc.register_count,
            )

    @classmethod
    def async_get_client_connection(
        cls, host: str, port: int
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
