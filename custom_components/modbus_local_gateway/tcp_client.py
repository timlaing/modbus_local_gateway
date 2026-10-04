"""TCP Client for Modbus Local Gateway"""

# The read and write paths are one class because they share the connection, the
# matching of answers to requests and the resynchronisation of a stream that has
# drifted out of step. Splitting them up is its own piece of work; until then this
# module is over the line pylint counts with, and not by much.
# pylint: disable=too-many-lines

import asyncio
from collections.abc import Callable
import logging
from typing import Any, cast

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import (
    ConnectionException,
    ModbusException,
    ModbusIOException,
)
from pymodbus.framer import FramerType
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
    WriteSingleRegisterResponse,
)

from .composite import CompositeConversion
from .context import ModbusContext
from .conversion import Conversion
from .entity_management.base import (
    ModbusCompositeEntityDescription,
    ModbusEntityDescription,
    ModbusFieldDescription,
)
from .entity_management.const import ModbusDataType, WriteFunction
from .exceptions import ModbusClientError, ModbusNoResponseError
from .transaction import MyTransactionManager

_LOGGER: logging.Logger = logging.getLogger(__name__)


def _padded_bit_count(read_count: int) -> int:
    """The number of bits a response to a request for ``read_count`` carries.

    Coils and discrete inputs are transmitted a byte at a time, so a request for
    up to eight of them is answered with eight bits, and so on. pymodbus decodes
    every bit of those bytes, which makes this the length of a well-formed answer.
    """
    return ((read_count + 7) // 8) * 8


# What one read of a poll cycle is remembered by: the device it went to, the
# bank it came from, and the range it covered.
ReadKey = tuple[int, ModbusDataType, int, int]


class AsyncModbusTcpClientGateway(AsyncModbusTcpClient):
    """Custom Modbus TCP client with request batching based on device and locking."""

    _CLIENT: dict[str, AsyncModbusTcpClientGateway] = {}

    # Diagnostics: how often a read did not leave the stream in a usable state
    # and the connection had to be resynchronised before the next request. A
    # count that keeps climbing names the TCP-to-RTU bridge, not the device.
    _resyncs: int = 0
    # Set when a transaction failed while the gateway was answering out of
    # order: only a new connection gets rid of the queued answers.
    _needs_reconnect: bool = False

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
        # The key this client is cached under, filled in by
        # `async_get_client_connection` once it knows host, port and framer.
        self._cache_key: str = ""
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
        self._resyncs = 0
        self._needs_reconnect = False

    @property
    def desynced(self) -> bool:
        """Whether the gateway is answering out of request order."""
        ctx = getattr(self, "ctx", None)
        return bool(getattr(ctx, "desynced", False))

    def _clear_desync(self) -> None:
        """Take the connection back out of the desynchronised state."""
        ctx = getattr(self, "ctx", None)
        if ctx is not None:
            ctx.clear_desync()

    def _flag_desync(self) -> bool:
        """Note a transaction that failed while the gateway was out of step.

        Returns whether the connection has to be renewed. Only a failure
        together with out-of-order answers means the bridge is holding
        responses nobody is waiting for: a failure on its own is a device that
        did not answer, so it does not justify dropping the connection.
        """
        if not self.desynced:
            return False
        self._needs_reconnect = True
        return True

    async def _ensure_connection(self) -> bool:
        """Connect, and renew the connection when the last transaction lost step.

        A gateway that bridges TCP to a serial bus keeps answering a request
        after the client has stopped waiting for it, so the next request collects
        that answer before its own. Renewing the connection drops what the bridge
        has queued, which is the only way back into step with it.
        """
        if self._needs_reconnect:
            _LOGGER.warning(
                "Gateway %s answered requests that were no longer waiting, renewing "
                "the connection to drop the queued answers",
                self,
            )
            self.close()
            if not await self.connect():
                # Left pending, so the next attempt renews rather than taking the
                # plain connection it would otherwise make and reading on a gateway
                # that is still out of step.
                _LOGGER.warning("Failed to reconnect to gateway - %s", self)
                return False
            self._clear_desync()
            self._needs_reconnect = False
            return True

        if not self.connected:
            await self.connect()
        if not self.connected:
            _LOGGER.warning("Failed to connect to gateway - %s", self)
            return False
        return True

    def _resync_transport(self) -> None:
        """Drop anything still buffered, and count the resynchronisation.

        Defensive rather than remedial: `pdu_send` already clears `recv_buffer`
        before every send, and clearing what has been received cannot unqueue an
        answer the gateway still owes. What does that is `_ensure_connection`.
        """
        self._resyncs += 1
        ctx = getattr(self, "ctx", None)
        if ctx is None:
            return
        ctx.recv_buffer = b""

    def _response_matches_request(
        self,
        response: ModbusPDU,
        is_register_func: bool,
        device_id: int,
        address: int,
        read_count: int,
    ) -> bool:
        """Whether the answer carries the registers or bits that were asked for.

        pymodbus has already matched the answer to the request by transaction
        id, so what is left to check is how much of it there is: a gateway that
        answers a request late hands back the answer to another one, and that
        shows up here as an answer of the wrong length. Coils come back in
        whole bytes, so the bits of a coil response span whole bytes: an answer
        may be longer than the request by up to the padding of the last byte,
        but no longer than that.
        """
        if not hasattr(response, "registers" if is_register_func else "bits"):
            _LOGGER.error("Invalid response received from Device ID %d", device_id)
            return False

        wrong_count: bool = (
            len(response.registers) != read_count
            if is_register_func
            else isinstance(response, (ReadCoilsResponse, ReadDiscreteInputsResponse))
            and not read_count <= len(response.bits) <= _padded_bit_count(read_count)
        )
        if not wrong_count:
            return True

        _LOGGER.error(
            (
                "Invalid response received from Device ID %d, "
                "address: %d (count does not match)"
            ),
            device_id,
            address,
        )
        return False

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

            if not self._response_matches_request(
                temp_response, is_register_func, device_id, current_address, read_count
            ):
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
        current: list[int] | None = None
        if any(field.is_bitfield for field in desc.fields):
            # A field that claims part of a register has to be merged into what
            # the device holds, or the bits it does not describe - a mode, an
            # enable, reserved bits - would be zeroed by the write. The whole
            # span is read once, in one transaction, inside `self.lock`.
            current = await self._read_current_registers(entity)
        pdu: ModbusPDU | None = None
        for run in desc.runs:
            registers: list[int] = self._run_registers(
                desc, run, field_values, conversion, current
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

    def _run_registers(
        self,
        desc: ModbusCompositeEntityDescription,
        run: tuple[ModbusFieldDescription, ...],
        field_values: dict[str, Any],
        conversion: Conversion,
        current: list[int] | None,
    ) -> list[int]:
        """Turn one run of fields into the registers to write for it.

        A field is placed at its own offset in the run, because two bit fields
        of the same register are one run and must end up in the same word. A bit
        field is merged into what `current` holds, so the bits around it - a
        mode, an enable, reserved bits - survive; every other register of the
        run starts from the device value and is overwritten by its field.

        `current` is None only when no field in the composite is a bit field,
        which is the case where a run can be written outright.
        """
        length: int = run[-1].end_address - run[0].address + 1
        base: int = run[0].address - desc.register_address
        registers: list[int] = (
            list(current[base : base + length]) if current is not None else [0] * length
        )
        for field in run:
            field_desc: ModbusEntityDescription = field.as_entity_description(
                desc.data_type
            )
            offset: int = field.address - run[0].address
            count: int = max(1, field.size)
            if field.is_bitfield:
                if current is None:
                    raise ModbusClientError(
                        f"Composite {desc.key} field {field.key} is a bit field "
                        "but no current registers were read"
                    )
                registers[offset : offset + count] = conversion.merge_into_registers(
                    field_desc,
                    field_values[field.key],
                    registers[offset : offset + count],
                )
            else:
                registers[offset : offset + count] = conversion.convert_to_registers(
                    field_desc, field_values[field.key]
                )
        return registers

    async def _write_holding_registers(
        self,
        entity: ModbusContext,
        value: Any,
        write_function: WriteFunction,
    ) -> ModbusPDU | None:
        """Write one entity's value to its holding registers"""
        conversion = Conversion(type(self))
        if entity.desc.conv_bits or entity.desc.conv_shift_bits:
            # No dependable device-side bit write (FC 0x16 is optional): read the
            # register, replace this field, write it back. Still inside
            # `self.lock`, so nothing lands in between.
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
        return await self._custom_write_registers(
            address=entity.desc.register_address,
            values=registers,
            device_id=entity.device_id,
            write_function=write_function,
        )

    async def _write_coil(self, entity: ModbusContext, value: Any) -> ModbusPDU:
        """Write one entity's value to its coil"""
        if not isinstance(value, bool):
            raise TypeError(
                f"Value for COIL must be boolean, got {type(value).__name__}"
            )
        return await self.write_coil(
            address=entity.desc.register_address,
            value=value,
            device_id=entity.device_id,
        )

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
            if not await self._ensure_connection():
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
                pdu = await self._write_holding_registers(entity, value, write_function)
            elif entity.desc.data_type == ModbusDataType.COIL:
                pdu = await self._write_coil(entity, value)
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
        """Fetch all values for a single device id.

        Raises `ModbusNoResponseError`, carrying what was read before the device
        stopped answering, so a cycle costs one timeout rather than one per entity.
        """
        data: dict[str, ModbusPDU] = {}
        # One poll cycle, one answer per register range: entities that read the
        # same registers are answered from the same transaction.
        cache: dict[ReadKey, ModbusPDU] = {}
        async with self.lock:
            if not await self._ensure_connection():
                return data

            for entity in entities:
                if not await self._process_entity(entity, data, max_read_size, cache):
                    raise ModbusNoResponseError(
                        f"Device ID {entity.device_id} stopped answering at "
                        f"{entity.desc.key}, after "
                        f"{len(data)} of {len(entities)} entities",
                        partial=data,
                    )
                if self._needs_reconnect:
                    # The rest of this poll would be read on a connection the
                    # gateway is not answering in step with, so it is left to
                    # the next poll, which starts on a renewed connection.
                    _LOGGER.debug(
                        "Ending the poll of %s early, the next one reconnects",
                        self,
                    )
                    break

            _LOGGER.debug("Update completed %s", self)

        return data

    async def _read_once(
        self,
        cache: dict[ReadKey, ModbusPDU],
        func: Callable[..., Any],
        device_id: int,
        data_type: ModbusDataType,
        address: int,
        count: int,
        max_read_size: int,
    ) -> ModbusPDU | None:
        """Read one register range, at most once per poll cycle.

        Entities of one device often share a register: a time window whose start
        time, mode and enable live in a single word is three entities on one
        address, and asking the device for that word once per entity triples the
        traffic of the poll without telling the caller anything new. The answer
        is kept for the rest of the cycle, so those entities report the same
        snapshot, and a failed read is not kept, so the next entity asks the
        device again rather than inheriting the failure.
        """
        key: ReadKey = (device_id, data_type, address, count)
        cached: ModbusPDU | None = cache.get(key)
        if cached is not None:
            _LOGGER.debug(
                "Reusing registers %d-%d for device %d from this cycle",
                address,
                address + count - 1,
                device_id,
            )
            return cached

        response: ModbusPDU | None = await self.read_data(
            func=func,
            address=address,
            count=count,
            device_id=device_id,
            max_read_size=max_read_size,
        )
        if response is not None and not response.isError():
            cache[key] = response
        return response

    async def _read_composite_runs(
        self,
        entity: ModbusContext,
        func: Callable[..., Any],
        max_read_size: int,
        cache: dict[ReadKey, ModbusPDU],
    ) -> ModbusPDU:
        """Read every run of adjacent registers a composite entity uses.

        Each run is read on its own, so the entity never asks for registers it
        does not use, and the runs are then stitched into a single response
        spanning the entity's whole register range - which is the shape
        `CompositeConversion` expects to read. A run another entity has already
        read in this cycle comes from that read instead of a new transaction.
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
            response: ModbusPDU | None = await self._read_once(
                cache,
                func,
                entity.device_id,
                desc.data_type,
                run[0].address,
                count,
                max_read_size,
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

    def _log_unusable_response(
        self, entity: ModbusContext, err: Exception | None = None
    ) -> None:
        """Report an answer that came back, but not the one that was asked for.

        The device is on the bus and talking, so this is a question about the data.
        """
        _LOGGER.debug(
            "No usable response for %s on device %d%s, resynchronised %d time(s)",
            entity.desc.key,
            entity.device_id,
            f": {err}" if err else "",
            self._resyncs,
        )

    def _log_no_response(self, entity: ModbusContext, exc: Exception) -> None:
        """Report a device that stopped answering, once per poll cycle."""
        _LOGGER.warning(
            "Device not available %s [%d]: %s; connection resynchronised %d time(s)",
            self,
            entity.device_id,
            exc,
            self._resyncs,
        )

    async def _process_entity(
        self,
        entity: ModbusContext,
        data: dict[str, ModbusPDU],
        max_read_size: int,
        cache: dict[ReadKey, ModbusPDU],
    ) -> bool:
        """Read one entity, reporting whether the device is still answering.

        False means the device went away: nothing came back at all. Every other
        outcome means it is talking, and the poll carries on.
        """
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
                    entity, func, max_read_size, cache
                )
            else:
                modbus_response = await self._read_once(
                    cache,
                    func,
                    entity.device_id,
                    entity.desc.data_type,
                    entity.desc.register_address,
                    # Treat empty list as "no scaling" to avoid zero-length reads
                    entity.desc.register_count
                    * (
                        max(1, len(entity.desc.conv_sum_scale))
                        if entity.desc.conv_sum_scale is not None
                        else 1
                    ),
                    max_read_size,
                )

            if modbus_response and not modbus_response.isError():
                data[entity.desc.key] = modbus_response
                # A matched answer clears the count.
                self._clear_desync()
                return True

            self._resync_transport()
            if not self._flag_desync():
                self._log_unusable_response(entity)
            return True

        except ModbusClientError as err:
            # An answer came back and could not be used - an exception response to
            # a composite read, for instance - so the device is there and the poll
            # carries on.
            self._log_unusable_response(entity, err)
            return True

        except (ModbusIOException, ConnectionException, TimeoutError) as err:
            # pymodbus raises these only after a device has failed to answer, so
            # this is the one case that says the device is no longer there.
            self._resync_transport()
            if not self._flag_desync():
                self._log_no_response(entity, err)
            return False

    @classmethod
    def async_get_client_connection(
        cls, host: str, port: int, connection_type: str
    ) -> AsyncModbusTcpClientGateway:
        """Gets a modbus client object"""
        key: str = f"{host}:{port}:{connection_type}"

        framer_type: FramerType = FramerType(connection_type)

        if key not in cls._CLIENT:
            _LOGGER.debug("Connecting to gateway %s", key)
            client = AsyncModbusTcpClientGateway(
                host=host,
                port=port,
                framer=framer_type,
                timeout=1.5,
                retries=5,
            )
            client._cache_key = key
            cls._CLIENT[key] = client
        return cls._CLIENT[key]

    def close_cached(self) -> None:
        """Close this client and drop it from the cache.

        Without this the connection to the gateway outlives the config entry:
        the socket stays open and pymodbus keeps retrying on it, so a disabled
        or reloaded entry is still talking to the device. On a gateway that
        bridges TCP to a shared serial bus, that leaked session corrupts the
        traffic of whoever is still connected.

        Only call this once no loaded entry is still using the client - it is
        shared by every entry with the same host, port and framer.

        The client is closed under the key it was cached under, not under the
        settings of the entry that is unloading: reconfiguring a gateway
        changes those, and closing the new key would leave the connection this
        client actually holds open.
        """
        key: str = self._cache_key
        if type(self)._CLIENT.pop(key, None) is not None:
            _LOGGER.debug("Closing connection to gateway %s", key)
            self.close()
