"""TCP Client for Modbus Local Gateway"""

import asyncio
from collections.abc import Callable
import logging
from typing import Any, cast

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
    WriteSingleRegisterResponse,
)

from .composite import CompositeConversion
from .context import ModbusContext
from .conversion import Conversion
from .entity_management.base import ModbusCompositeEntityDescription
from .entity_management.const import ModbusDataType, WriteFunction
from .transaction import MyTransactionManager

_LOGGER: logging.Logger = logging.getLogger(__name__)


class ModbusClientError(ModbusException):
    """Typed Modbus client error."""

    def __init__(self, string: str) -> None:
        """Initialize the error."""
        super().__init__(string)  # type: ignore[no-untyped-call]
        self.string = string


class AsyncModbusTcpClientGateway(AsyncModbusTcpClient):
    """Custom Modbus TCP client with request batching based on device and locking."""

    _CLIENT: dict[str, AsyncModbusTcpClientGateway] = {}

    def __init__(
        self,
        host: str,
        port: int = 502,
        framer: FramerType = FramerType.SOCKET,
        source_address: tuple[str, int] | None = None,
        **kwargs: Any,
    ) -> None:
        self._data_type_function_mapping: dict[str, Callable[..., Any]] = {
            ModbusDataType.HOLDING_REGISTER: self.read_holding_registers,
            ModbusDataType.INPUT_REGISTER: self.read_input_registers,
            ModbusDataType.COIL: self.read_coils,
            ModbusDataType.DISCRETE_INPUT: self.read_discrete_inputs,
        }
        self.lock = asyncio.Lock()
        # Devices that have answered a preset single register write. Silence
        # from a device outside this set means the function is not implemented
        # rather than that a response went missing, which is what makes retrying
        # such a write with preset multiple registers safe.
        self._devices_answering_fc06: set[int] = set()
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
        self,
        func: Callable[..., Any],
        address: int,
        count: int,
        device_id: int,
        max_read_size: int,
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
                device_id=device_id,
            )

            if not hasattr(temp_response, "registers" if is_register_func else "bits"):
                _LOGGER.error("Invalid response received from Device ID %d", device_id)
                return None

            if (
                is_register_func
                and hasattr(temp_response, "registers")
                and len(temp_response.registers) != read_count
            ):
                _LOGGER.error(
                    (
                        "Invalid response received from Device ID %d, "
                        "address: %d (count does not match)"
                    ),
                    device_id,
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
        self,
        address: int,
        values: list[int],
        device_id: int,
        write_function: WriteFunction = WriteFunction.SINGLE,
    ) -> ModbusPDU | None:
        """Write values to Modbus registers.

        The write function is chosen from the number of values, unless
        `write_function` selects one explicitly: some devices only implement
        preset multiple registers (FC 0x10) and ignore preset single register
        (FC 0x06), including for a single value.

        Returns the last PDU received so the caller can detect an error
        response; None only when there was nothing to write.
        """
        if not values:
            _LOGGER.debug("No values to write, skipping.")
            return None

        if write_function == WriteFunction.MULTIPLE or len(values) > 1:
            return await self._write_multiple_registers(address, values, device_id)
        return await self._write_single_register(address, values[0], device_id)

    async def _write_single_register(
        self, address: int, value: int, device_id: int
    ) -> ModbusPDU:
        """Write a single value to a Modbus register.

        Falls back to preset multiple registers (FC 0x10) when the device does
        not implement preset single register (FC 0x06): such a device either
        answers with an exception or stays silent, and the write is lost.
        """
        _LOGGER.debug(
            "Writing single value %d to register at address %d, device_id %d",
            value,
            address,
            device_id,
        )
        try:
            result: ModbusPDU = await self.write_register(
                address=address,
                value=value,
                device_id=device_id,
            )
        except (ModbusException, TimeoutError) as exc:
            return await self._write_single_register_unanswered(
                address, value, device_id, exc
            )
        if result.isError():
            # An exception response means the device rejected the request without
            # carrying it out, so FC 0x10 can safely be handed the same value.
            return await self._retry_single_with_multiple_registers(
                address, value, device_id, f"it was refused: {result}"
            )
        _LOGGER.debug("Writing successful")
        self._devices_answering_fc06.add(device_id)
        return result

    async def _write_single_register_unanswered(
        self, address: int, value: int, device_id: int, exc: Exception
    ) -> ModbusPDU:
        """Deal with a single-register write that never got an answer.

        A matching read-back is not proof that the write ran - the register may
        have held the value already - but it does mean the requested state is
        in place, so the write is reported as done and not repeated.

        What a read-back that still shows the old value cannot settle is why
        nothing came back: a device that does not implement preset single
        register drops it, while a device that does implement it may have run a
        command and lost only the response. Repeating the write is safe in the
        first case and can run a command register twice in the second, so the
        FC 0x10 retry is limited to devices that have never answered preset
        single register. A read that cannot be answered leaves it unknown, and
        then nothing is repeated.
        """
        applied: bool | None = await self._write_was_applied(address, value, device_id)
        if applied:
            _LOGGER.warning(
                "No answer writing value %d to address %d (%s), but the register "
                "already holds it, so the write is treated as done and not "
                "repeated",
                value,
                address,
                exc,
            )
            return WriteSingleRegisterResponse(address=address, registers=[value])
        if applied is None:
            raise ModbusClientError(
                f"No answer writing value {value} to address {address} ({exc}) and "
                "the register could not be read back, so the write is not repeated"
            )
        if device_id in self._devices_answering_fc06:
            raise ModbusClientError(
                f"No answer writing value {value} to address {address} ({exc}) from "
                "a device that answers preset single register, so the write is not "
                "repeated: repeating it could run a command register twice"
            )
        return await self._retry_single_with_multiple_registers(
            address, value, device_id, f"it went unanswered ({exc})"
        )

    async def _write_was_applied(
        self, address: int, value: int, device_id: int
    ) -> bool | None:
        """Whether the register holds `value`, or None when that is unknowable.

        Read under the lock `write_data()` holds, so no poll can change the
        register between the write and this read.
        """
        try:
            response: ModbusPDU = await self.read_holding_registers(
                address=address, count=1, device_id=device_id
            )
        except ModbusException, TimeoutError:
            _LOGGER.debug(
                "Could not read back address %d after an unanswered write", address
            )
            return None
        if response is None or response.isError() or not response.registers:
            return None
        return bool(response.registers[0] == value)

    async def _retry_single_with_multiple_registers(
        self, address: int, value: int, device_id: int, reason: str
    ) -> ModbusPDU:
        """Repeat a write that did not happen with preset multiple registers.

        Sent straight through `write_registers` rather than through
        `_write_multiple_registers()`, whose own fallback writes the register
        one at a time - repeating the function that just failed.
        """
        _LOGGER.warning(
            "Preset single register failed for value %d at address %d (%s). "
            "Retrying with preset multiple registers",
            value,
            address,
            reason,
        )
        result: ModbusPDU = await self.write_registers(
            address=address,
            values=[value],
            device_id=device_id,
        )
        if result.isError():
            _LOGGER.error(
                "Failed to write value %d to address %d: %s",
                value,
                address,
                result,
            )
        else:
            _LOGGER.debug(
                "Writing single value %d to address %d succeeded with preset "
                "multiple registers",
                value,
                address,
            )
        return result

    async def _write_multiple_registers(
        self, address: int, values: list[int], device_id: int
    ) -> ModbusPDU:
        """Write multiple values to Modbus registers."""
        _LOGGER.debug(
            "Attempting to write multiple values %s starting at address %d, "
            "device_id %d using write_registers",
            values,
            address,
            device_id,
        )
        result: ModbusPDU = await self.write_registers(
            address=address,
            values=values,
            device_id=device_id,
        )
        if result.isError():
            _LOGGER.warning(
                "Failed to write multiple values using write_registers: %s. "
                "Falling back to old method (individual write_register calls).",
                result,
            )
            fallback: ModbusPDU | None = await self._write_registers_individually(
                address, values, device_id
            )
            return fallback if fallback is not None else result
        _LOGGER.debug("Writing multiple values using write_registers successful")
        return result

    async def _write_registers_individually(
        self, address: int, values: list[int], device_id: int
    ) -> ModbusPDU | None:
        """Fallback method to write multiple values to Modbus registers individually.

        Returns the first error PDU encountered, or the last successful one.
        """
        result: ModbusPDU | None = None
        for i, value in enumerate(values):
            current_address = address + i
            _LOGGER.debug(
                "Writing value %d to register at address %d, device_id %d",
                value,
                current_address,
                device_id,
            )
            result = await self.write_register(
                address=current_address, value=value, device_id=device_id
            )
            if result.isError():
                _LOGGER.error(
                    "Failed to write value %d to address %d: %s",
                    value,
                    current_address,
                    result,
                )
                return result
        _LOGGER.debug("All individual writes successful using fallback")
        return result

    async def _read_current_registers(self, entity: ModbusContext) -> list[int]:
        """Read the register(s) backing a bit field, for a read-modify-write.

        Must be called with the client lock held, so the read and the write it
        feeds cannot be interleaved with a poll.

        The span is read in one transaction rather than in `max_register_read`
        chunks: a field split across two reads could tear if the device changed
        in between. A failed read raises, abandoning the write - merging onto a
        guess would clear the field's neighbours.
        """
        span_read_count: int = entity.desc.register_count or 1
        response: ModbusPDU | None = await self.read_data(
            func=self.read_holding_registers,
            address=entity.desc.register_address,
            count=span_read_count,
            device_id=entity.device_id,
            max_read_size=span_read_count,
        )
        if response is None or response.isError():
            raise ModbusClientError(
                "Unable to read current value of "
                f"{entity.desc.key} at {entity.desc.register_address} - "
                "aborting bit field write"
            )
        return response.registers

    async def _write_composite(
        self,
        entity: ModbusContext,
        value: Any,
        write_function: WriteFunction,
    ) -> ModbusPDU:
        """Write a composite entity as one request per run of adjacent registers.

        Grouping the fields keeps the device from being left with a half updated
        value: a clock written as one preset multiple registers request changes
        year to second together, and only fields that are not adjacent to each
        other need a request of their own.
        """
        desc: ModbusCompositeEntityDescription = cast(
            ModbusCompositeEntityDescription, entity.desc
        )
        if desc.data_type != ModbusDataType.HOLDING_REGISTER:
            raise ModbusClientError(
                f"Composite {desc.key} is declared as {desc.data_type} and "
                "cannot be written"
            )

        field_values: dict[str, Any] = CompositeConversion.to_field_values(desc, value)
        conversion: Conversion = Conversion(type(self))
        pdu: ModbusPDU | None = None
        for run in desc.runs:
            registers: list[int] = []
            for field in run:
                registers += conversion.convert_to_registers(
                    field.as_entity_description(desc.data_type),
                    field_values[field.key],
                )
            _LOGGER.debug(
                "Writing composite %s run %s to address %d",
                desc.key,
                ", ".join(field.key for field in run),
                run[0].address,
            )
            run_pdu: ModbusPDU | None = await self._custom_write_registers(
                address=run[0].address,
                values=registers,
                device_id=entity.device_id,
                write_function=write_function,
            )
            if run_pdu is None:
                raise ModbusClientError(
                    f"No response writing composite {desc.key} to registers "
                    f"{run[0].address}-{run[-1].end_address}"
                )
            if run_pdu.isError():
                raise ModbusClientError(
                    f"Error writing {desc.key} to registers "
                    f"{run[0].address}-{run[-1].end_address}: {run_pdu}"
                )
            pdu = run_pdu

        if pdu is None:
            raise ModbusClientError(f"Composite {desc.key} declares no fields")
        return pdu

    async def write_data(
        self,
        entity: ModbusContext,
        value: Any,
        write_function: WriteFunction = WriteFunction.SINGLE,
    ) -> ModbusPDU | None:
        """Writes data to Holding Registers or Coils.

        `write_function` is read from the config entry rather than stored on the
        client, because one client is shared by every entry pointing at the same
        gateway.
        """
        pdu: ModbusPDU | None = None
        async with self.lock:
            if not self.connected:
                await self.connect()
                if not self.connected:
                    _LOGGER.warning("Failed to connect to gateway - %s", self)
                    return None

            _LOGGER.debug(
                "Starting write operation - Device ID: %d, %s (%s): %d, Count: %d",
                entity.device_id,
                entity.desc.data_type,
                entity.desc.key,
                entity.desc.register_address,
                entity.desc.register_count,
            )
            _LOGGER.debug(
                "Value before conversion: %s (type: %s)", value, type(value).__name__
            )

            if isinstance(entity.desc, ModbusCompositeEntityDescription):
                pdu = await self._write_composite(entity, value, write_function)
            elif entity.desc.data_type == ModbusDataType.HOLDING_REGISTER:
                conversion = Conversion(type(self))
                if entity.desc.conv_bits or entity.desc.conv_shift_bits:
                    # No dependable device-side bit write (FC 0x16 is optional):
                    # read the register, replace this field, write it back. Still
                    # inside `self.lock`, so nothing lands in between.
                    registers = conversion.merge_into_registers(
                        entity.desc,
                        value,
                        await self._read_current_registers(entity),
                    )
                else:
                    registers = conversion.convert_to_registers(entity.desc, value)
                _LOGGER.debug(
                    "Raw value after conversion to registers: %s (type: %s)",
                    registers,
                    type(registers).__name__,
                )
                if len(registers) != entity.desc.register_count:
                    raise ModbusClientError(
                        "Incorrect number of registers: expected "
                        f"{entity.desc.register_count}, got {len(registers)}"
                    )
                pdu = await self._custom_write_registers(
                    address=entity.desc.register_address,
                    values=registers,
                    device_id=entity.device_id,
                    write_function=write_function,
                )
            elif entity.desc.data_type == ModbusDataType.COIL:
                if not isinstance(value, bool):
                    raise TypeError(
                        f"Value for COIL must be boolean, got {type(value).__name__}"
                    )
                pdu = await self.write_coil(
                    address=entity.desc.register_address,
                    value=value,
                    device_id=entity.device_id,
                )
            else:
                raise ValueError(f"Unsupported data type: {entity.desc.data_type}")

            if pdu and pdu.isError():
                _LOGGER.error(
                    "Error writing data to %s (%s): %s",
                    entity.desc.key,
                    entity.desc.data_type,
                    pdu,
                )
                raise ModbusClientError(
                    f"Error writing data to {entity.desc.key} "
                    f"({entity.desc.data_type}): {pdu}"
                )

            return pdu

    async def update_device(
        self, entities: list[ModbusContext], max_read_size: int
    ) -> dict[str, ModbusPDU]:
        """Fetches all values for a single device id"""
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

    async def _read_composite_runs(
        self,
        entity: ModbusContext,
        func: Callable[..., Any],
        max_read_size: int,
    ) -> ModbusPDU:
        """Read every run of adjacent registers a composite entity uses.

        Each run is read on its own, so the entity never asks for registers it
        does not use, and the runs are then stitched into a single response
        spanning the entity's whole register range - which is the shape
        `CompositeConversion` expects to read.
        """
        desc: ModbusCompositeEntityDescription = cast(
            ModbusCompositeEntityDescription, entity.desc
        )
        registers: list[int] = [0] * (desc.register_count or 0)
        response_class: type[ModbusPDU] = (
            ReadHoldingRegistersResponse
            if desc.data_type == ModbusDataType.HOLDING_REGISTER
            else ReadInputRegistersResponse
        )

        for run in desc.runs:
            count: int = run[-1].end_address - run[0].address + 1
            response: ModbusPDU | None = await self.read_data(
                func=func,
                address=run[0].address,
                count=count,
                device_id=entity.device_id,
                max_read_size=max_read_size,
            )
            if response is None:
                raise ModbusClientError(
                    f"No response reading composite {desc.key} from registers "
                    f"{run[0].address}-{run[-1].end_address}"
                )
            if response.isError():
                raise ModbusClientError(
                    f"Error reading composite {desc.key} from registers "
                    f"{run[0].address}-{run[-1].end_address}: {response}"
                )
            start: int = run[0].address - desc.register_address
            registers[start : start + count] = list(response.registers)

        _LOGGER.debug(
            "Composite %s stitched %d registers: %s",
            desc.key,
            desc.register_count,
            registers,
        )
        return response_class(registers=registers)

    async def _process_entity(
        self,
        entity: ModbusContext,
        data: dict[str, ModbusPDU],
        idx: int,
        max_read_size: int,
    ) -> None:
        """Process a single entity and update the data dictionary"""
        _LOGGER.debug(
            "Reading Device ID: %d, register/coil (%s): %d, count: %d",
            entity.device_id,
            entity.desc.key,
            entity.desc.register_address,
            entity.desc.register_count,
        )
        func: Callable[..., Any] | None = self._data_type_function_mapping.get(
            entity.desc.data_type
        )
        if func is None:
            raise ValueError(f"Invalid data type: {entity.desc.data_type}")
        if entity.desc.register_count is None or entity.desc.register_count == 0:
            raise ValueError("Invalid register count")

        try:
            modbus_response: ModbusPDU | None
            if isinstance(entity.desc, ModbusCompositeEntityDescription):
                modbus_response = await self._read_composite_runs(
                    entity, func, max_read_size
                )
            else:
                modbus_response = await self.read_data(
                    func=func,
                    address=entity.desc.register_address,
                    # Treat empty list as "no scaling" to avoid zero-length reads
                    count=entity.desc.register_count
                    * (
                        max(1, len(entity.desc.conv_sum_scale))
                        if entity.desc.conv_sum_scale is not None
                        else 1
                    ),
                    device_id=entity.device_id,
                    max_read_size=max_read_size,
                )

            if modbus_response and not modbus_response.isError():
                data[entity.desc.key] = modbus_response
            else:
                _LOGGER.debug("Error reading %s", entity.desc.key)

        except ModbusException, TimeoutError:
            if idx == 0:
                _LOGGER.warning(
                    "Device not available %s [%d]",
                    self,
                    entity.device_id,
                )
                return
            _LOGGER.debug(
                "Unable to retrieve value for Device ID %d, register/coil (%s): "
                "%d, count: %d",
                entity.device_id,
                entity.desc.key,
                entity.desc.register_address,
                entity.desc.register_count,
            )

    @classmethod
    def async_get_client_connection(
        cls, host: str, port: int, connection_type: str
    ) -> AsyncModbusTcpClientGateway:
        """Gets a modbus client object"""
        key: str = f"{host}:{port}:{connection_type}"

        framer_type: FramerType = FramerType(connection_type)

        if key not in cls._CLIENT:
            _LOGGER.debug("Connecting to gateway %s", key)
            cls._CLIENT[key] = AsyncModbusTcpClientGateway(
                host=host,
                port=port,
                framer=framer_type,
                timeout=1.5,
                retries=5,
            )
        return cls._CLIENT[key]

    @classmethod
    def close_client_connection(
        cls, host: str, port: int, connection_type: str
    ) -> None:
        """Close a cached client and drop it from the cache.

        Without this the connection to the gateway outlives the config entry:
        the socket stays open and pymodbus keeps retrying on it, so a disabled
        or reloaded entry is still talking to the device. On a gateway that
        bridges TCP to a shared serial bus, that leaked session corrupts the
        traffic of whoever is still connected.

        Only call this once no loaded entry is still using the client - it is
        shared by every entry with the same host, port and framer.
        """
        key: str = f"{host}:{port}:{connection_type}"
        client: AsyncModbusTcpClientGateway | None = cls._CLIENT.pop(key, None)
        if client is not None:
            _LOGGER.debug("Closing connection to gateway %s", key)
            client.close()
