"""TCP Client for Modbus Local Gateway"""

# The read and write paths are one class because they share the connection, the
# matching of answers to requests and the resynchronisation of a stream that has
# drifted out of step. Splitting them up is its own piece of work; until then this
# module is over the line pylint counts with, and not by much.
# pylint: disable=too-many-lines

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
from time import monotonic
from typing import Any, NoReturn, cast

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

# How long a device that has stopped answering is left alone before it is asked
# again, in seconds. A solar inverter is off for hours and a device unplugged for
# the afternoon is no different, so this grows and then stops growing: asked
# every few seconds it would be a device talking to a device that is not there,
# and asked once an hour it would be a slow recovery. One step per failed probe,
# bounded at the last step.
_PROBE_BACKOFF: tuple[int, ...] = (5, 10, 20, 40, 80, 120)

# The same idea for the gateway itself, on a shorter ladder: a gateway that is not
# answering is usually back in seconds, and it is retried once per device behind
# it, so leaving it alone briefly is what keeps a power cycle from being a
# reconnect storm.
_CONNECT_BACKOFF: tuple[int, ...] = (2, 5, 15, 30, 60)


def _step(backoff: tuple[int, ...], failures: int) -> float:
    """The wait before the next attempt: one step per failure, bounded by the last."""
    return float(backoff[min(max(failures, 1) - 1, len(backoff) - 1)])


@dataclass
class _Outage:
    """What is known about one device that stopped answering.

    Kept per slave id on the client rather than on a coordinator, because every
    way of asking a device for a value arrives here - a shared refresh, an entity
    on its own `scan_interval`, a recovery probe - and they all have to obey the
    same state and say the same thing about it.
    """

    # How many probes have been asked since the device last answered. The first
    # is short, the last is bounded: see `_PROBE_BACKOFF`.
    failures: int = 0
    # When the next probe is due, on the monotonic clock.
    next_probe: float = 0.0
    # When the device stopped answering, on the same clock, for the recovery line.
    since: float = 0.0
    # Why it is believed to be away, said once with the transition.
    reason: str = ""

    @property
    def due(self) -> bool:
        """Whether the device is due to be asked again."""
        return monotonic() >= self.next_probe


@dataclass(frozen=True)
class DevicePolicy:
    """How a device is polled while it is not answering.

    Passed per poll rather than stored, because it comes from the settings of one
    device behind a gateway whose client is shared with every other device on it.
    """

    # Whether this poll is for the whole device, as a shared refresh is, or for
    # one entity on its own timer. A read of one entity that gets nothing back
    # says nothing about the rest of the device, so it is not taken as the
    # device going away.
    whole_device: bool = True
    # The entity a recovery probe reads, named by the device's own configuration.
    # `None` means the first entity of the refresh. A refresh that does not cover
    # the entity that was named falls back to its own first entity too, and a read
    # of one entity never probes at all.
    probe_key: str | None = None
    # Whether this device is expected to stop answering, e.g. a solar inverter
    # after dark. Its transitions are logged as information rather than as a
    # fault; it is still probed and its entities are still unavailable.
    expected_offline: bool = False


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
        # Whether the last connection attempt got through. Reported on the change,
        # not per attempt: every device behind the gateway retries on its own
        # schedule, so a warning per attempt is a warning every few seconds for as
        # long as the gateway stays away.
        self._gateway_reachable: bool = True
        # What is known about each device that has stopped answering, by slave id.
        # The gateway has its own gate below, because it is a different thing: a
        # device that is off is asked again, a gateway that is off is connected.
        self._outages: dict[int, _Outage] = {}
        # How long the gateway itself is left alone after a failed connection
        # attempt, and how many have failed.
        self._connect_next_attempt: float = 0.0
        self._connect_failures: int = 0

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

    async def _ensure_connection(self, *, gated: bool = True) -> bool:
        """Connect, and renew the connection when the last transaction lost step.

        A gateway that bridges TCP to a serial bus keeps answering a request
        after the client has stopped waiting for it, so the next request collects
        that answer before its own. Renewing the connection drops what the bridge
        has queued, which is the only way back into step with it.

        After a failed attempt the gateway is left alone until the next one is
        due, which is what stops every device behind it retrying the same dead
        gateway once per refresh interval. `gated` is False for a write, which is
        asked for by a person waiting for it rather than by a timer.
        """
        if gated and self._connect_next_attempt > monotonic():
            self._report_reachable(False)
            return False
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
                self._note_unreachable()
                return False
            self._clear_desync()
            self._needs_reconnect = False
            self._note_reachable()
            return True

        if not self.connected:
            await self.connect()
        if not self.connected:
            self._note_unreachable()
            return False
        self._note_reachable()
        return True

    def _note_unreachable(self) -> None:
        """Record a connection attempt that did not get through.

        The next attempt is put off for a while rather than being made by the next
        device that refreshes: one gateway that is down is otherwise one failed
        connect per device per refresh interval.
        """
        self._connect_failures += 1
        self._connect_next_attempt = monotonic() + _step(
            _CONNECT_BACKOFF, self._connect_failures
        )
        self._report_reachable(False)

    def _note_reachable(self) -> None:
        """Record a connection that got through, and let the next failure start over."""
        self._connect_failures = 0
        self._connect_next_attempt = 0.0
        self._report_reachable(True)

    def _report_reachable(self, reachable: bool) -> None:
        """Report a gateway going away or coming back, once per change."""
        if reachable == self._gateway_reachable:
            return
        self._gateway_reachable = reachable
        if reachable:
            _LOGGER.info("Gateway %s is reachable again", self)
        else:
            _LOGGER.info("Gateway %s is not reachable", self)

    def device_online(self, device_id: int) -> bool:
        """Whether the device answered its last read.

        Read by the coordinator for availability, so a device whose recovery
        probe succeeds is available again without waiting for a poll that the
        backoff may still be holding off.
        """
        return device_id not in self._outages

    def _note_gone(self, device_id: int, reason: str, expected_offline: bool) -> None:
        """Record a device that stopped answering, and say so once.

        A device that is off is asked again on every cycle, so a line per cycle
        is a line every few seconds for as long as it is off. The one thing worth
        having is the transition, and when it is over: the next probe is put off
        rather than the next read being skipped forever.
        """
        outage: _Outage | None = self._outages.get(device_id)
        if outage is None:
            outage = _Outage(since=monotonic(), reason=reason)
            self._outages[device_id] = outage
        outage.failures += 1
        outage.reason = reason
        outage.next_probe = monotonic() + _step(_PROBE_BACKOFF, outage.failures)
        if outage.failures > 1:
            _LOGGER.debug(
                "Device ID %d on gateway %s still not answering (%s), next probe in "
                "%d s",
                device_id,
                self,
                reason,
                int(outage.next_probe - monotonic()),
            )
            return
        _LOGGER.log(
            logging.INFO if expected_offline else logging.WARNING,
            "Device ID %d on gateway %s stopped answering (%s); its entities are "
            "unavailable and it is polled again in %d s",
            device_id,
            self,
            reason,
            int(outage.next_probe - outage.since),
        )

    def _note_answering(self, device_id: int) -> None:
        """Record a device that is answering again, and say so once."""
        outage: _Outage | None = self._outages.pop(device_id, None)
        if outage is None:
            return
        _LOGGER.info(
            "Device ID %d on gateway %s is answering again, silent for %d s (%s)",
            device_id,
            self,
            int(monotonic() - outage.since),
            outage.reason,
        )

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

    async def _read_current_registers(
        self,
        entity: ModbusContext,
        address: int | None = None,
        count: int | None = None,
    ) -> list[int]:
        """Read the register(s) backing an entity, for a read-modify-write.

        Must be called with the client lock held, so the read and the write it
        feeds cannot be interleaved with a poll.

        The span is read in one transaction rather than in `max_register_read`
        chunks: a field split across two reads could tear if the device changed
        in between. A failed read raises, abandoning the write - merging onto a
        guess would clear the field's neighbours.

        `address`/`count` default to the entity's own span; a composite with
        `write_with` passes the wider span its write rewrites.
        """
        read_address: int = entity.desc.register_address if address is None else address
        span_read_count: int = (
            entity.desc.register_count or 1 if count is None else count
        )
        response: ModbusPDU | None = await self.read_data(
            func=self.read_holding_registers,
            address=read_address,
            count=span_read_count,
            device_id=entity.device_id,
            max_read_size=span_read_count,
        )
        if response is None or response.isError():
            raise ModbusClientError(
                "Unable to read current value of "
                f"{entity.desc.key} at {read_address} - "
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

        `write_function` on the description overrides the connection's choice
        for a device that will not take a whole run in one request: declared
        single, the run is written one register at a time.
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
        if desc.write_with:
            # A device may want the paired register rewritten together with the
            # field, e.g. a window's start and end in one request. The whole
            # write span - fields and the declared registers - is seeded from
            # the current values, so the partner keeps its value while the
            # field is merged into it, then written as one block.
            write_start, write_end = desc.write_span
            current: list[int] | None = await self._read_current_registers(
                entity, write_start, write_end - write_start + 1
            )
            registers: list[int] = self._span_registers(
                desc,
                write_start,
                write_end,
                field_values,
                conversion,
                current,
            )
            _LOGGER.debug(
                "Writing composite %s to registers %d-%d",
                desc.key,
                write_start,
                write_end,
            )
            pdu = await self._write_run_registers(
                address=write_start,
                values=registers,
                device_id=entity.device_id,
                write_function=write_function,
                declared=desc.write_function,
            )
        else:
            current = None
            if any(field.is_bitfield for field in desc.fields):
                # A field that claims part of a register has to be merged into
                # what the device holds, or the bits it does not describe - a
                # mode, an enable, reserved bits - would be zeroed by the
                # write. The whole span is read once, in one transaction,
                # inside `self.lock`.
                current = await self._read_current_registers(entity)
            for run in desc.runs:
                registers = self._run_registers(
                    desc, run, field_values, conversion, current
                )
                _LOGGER.debug(
                    "Writing composite %s run %s to address %d",
                    desc.key,
                    ", ".join(field.key for field in run),
                    run[0].address,
                )
                pdu = await self._write_run_registers(
                    address=run[0].address,
                    values=registers,
                    device_id=entity.device_id,
                    write_function=write_function,
                    declared=desc.write_function,
                )
                if pdu is None:
                    raise ModbusClientError(
                        f"No response writing composite {desc.key} to registers "
                        f"{run[0].address}-{run[-1].end_address}"
                    )
                if pdu.isError():
                    raise ModbusClientError(
                        f"Error writing {desc.key} to registers "
                        f"{run[0].address}-{run[-1].end_address}: {pdu}"
                    )

        if pdu is None:
            raise ModbusClientError(f"Composite {desc.key} declares no fields")
        if pdu.isError():
            raise ModbusClientError(f"Error writing {desc.key}: {pdu}")
        return pdu

    async def _write_run_registers(
        self,
        address: int,
        values: list[int],
        device_id: int,
        write_function: WriteFunction,
        declared: WriteFunction | None,
    ) -> ModbusPDU | None:
        """Write the registers of one run, one request per register if asked.

        `declared` is what the composite asked for, and it wins over the
        connection's own `write_function` even for a run of one register: a
        device that refuses the block write over a clock would reject the run as
        soon as one register made it a block write again. `single` sends each
        register as its own request, each keeping the per-register fallback to
        FC 0x10 that a single write already has. The first register the device
        refuses ends the run and its response is returned, so a clock left
        partly updated is never reported as written.

        Without a declaration the run is one request whatever the connection
        would otherwise choose, which is how every other device config writes.
        """
        if declared is None:
            return await self._custom_write_registers(
                address=address,
                values=values,
                device_id=device_id,
                write_function=write_function,
            )
        if declared == WriteFunction.MULTIPLE:
            return await self._write_multiple_registers(address, values, device_id)

        pdu: ModbusPDU | None = None
        for offset, value in enumerate(values):
            pdu = await self._write_single_register(address + offset, value, device_id)
            if pdu.isError():
                return pdu
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
                registers[offset : offset + count] = field.apply_write_offset(
                    conversion.convert_to_registers(field_desc, field_values[field.key])
                )
        return registers

    def _span_registers(
        self,
        desc: ModbusCompositeEntityDescription,
        span_start: int,
        span_end: int,
        field_values: dict[str, Any],
        conversion: Conversion,
        current: list[int] | None,
    ) -> list[int]:
        """Turn the whole write span into the registers to write for it.

        `write_with` registers are not fields, so they start from `current` -
        the read that also feeds the bit field merges - and keep whatever the
        device holds. Fields are placed at their own offset inside the span,
        which may start one or more registers before the first field: a pair
        is then written together as one request whose first register is the
        partner the device wants rewritten too.
        """
        length: int = span_end - span_start + 1
        registers: list[int] = (
            list(current[:length]) if current is not None else [0] * length
        )
        for field in desc.fields:
            field_desc: ModbusEntityDescription = field.as_entity_description(
                desc.data_type
            )
            offset: int = field.address - span_start
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
                registers[offset : offset + count] = field.apply_write_offset(
                    conversion.convert_to_registers(field_desc, field_values[field.key])
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
            # Not gated: a write is asked for by a person waiting for it, and the
            # only thing the outage gate does to a write is delay telling them it
            # did not get through. Nothing written here is replayed on recovery.
            if not await self._ensure_connection(gated=False):
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
        self,
        entities: list[ModbusContext],
        max_read_size: int,
        policy: DevicePolicy | None = None,
    ) -> dict[str, ModbusPDU]:
        """Fetch all values for a single device id.

        Raises `ModbusNoResponseError`, carrying what was read before the device
        stopped answering, so a cycle costs one timeout rather than one per entity.

        While a device is backing off from having stopped answering, this reads
        nothing at all: the read is due when the next probe is, and until then the
        device is not talked to. Nothing is awaited while waiting, so the lock this
        holds is held for the length of one read at most, and a device behind this
        gateway that is awake keeps polling.
        """
        data: dict[str, ModbusPDU] = {}
        if not entities:
            return data
        device_id: int = entities[0].device_id
        expected_offline: bool = policy.expected_offline if policy else False
        whole_device: bool = policy.whole_device if policy else True
        # One poll cycle, one answer per register range: entities that read the
        # same registers are answered from the same transaction.
        cache: dict[ReadKey, ModbusPDU] = {}
        # What this cycle actually asked the device for, so an entity left out by
        # an early end is not counted as one the device failed to answer.
        asked: list[ModbusContext] = []
        async with self.lock:
            if not await self._ensure_connection():
                return data

            outage: _Outage | None = self._outages.get(device_id)
            if outage is not None:
                probe = await self._probe_for_return(
                    entities, outage, policy, data, cache, max_read_size
                )
                if probe is None:
                    return data
                asked.append(probe)

            for entity in entities:
                if entity.desc.key in data:
                    # Already answered by the recovery probe above.
                    continue
                if not await self._process_entity(entity, data, max_read_size, cache):
                    self._note_unanswered(
                        entity, entities, data, asked, whole_device, expected_offline
                    )
                asked.append(entity)
                if self._needs_reconnect:
                    # The rest of this poll would be read on a connection the
                    # gateway is not answering in step with, so it is left to the
                    # next poll, which starts on a renewed connection.
                    _LOGGER.debug(
                        "Ending the poll of %s early, the next one reconnects",
                        self,
                    )
                    break

            self._note_answering(device_id)
            self._report_unusable(asked, data)
            _LOGGER.debug("Update completed %s", self)

        return data

    def _note_unanswered(
        self,
        entity: ModbusContext,
        entities: list[ModbusContext],
        data: dict[str, ModbusPDU],
        asked: list[ModbusContext],
        whole_device: bool,
        expected_offline: bool,
    ) -> NoReturn:
        """Say what a read that got nothing back means, and end the poll.

        What it means depends on what else the poll has: something already in `data`
        means the device answered part of this poll, and nothing at all in a poll of
        the whole device means it has stopped answering. Raises
        `ModbusNoResponseError` carrying what was read, either way.
        """
        device_id: int = entity.device_id
        reason = f"after {len(data)} of {len(entities)} entities, at {entity.desc.key}"
        if data:
            # The device answered part of this poll, so it is on the bus and the
            # silence is about one read rather than the device. It is warned
            # about, once per poll, naming what it did not answer, and the next
            # poll asks again as normal: backing off here would hide a device that
            # is answering intermittently behind "it has stopped answering", and
            # would publish the values it did answer as unavailable along with the
            # one it did not.
            self._report_unusable(asked + [entity], data)
        elif whole_device:
            self._note_gone(device_id, reason, expected_offline)
        else:
            # One entity on its own timer got nothing back. It says nothing about
            # the rest of the device, so the device is not put on a backoff over
            # it, and it is not warned about every cycle either: the entity is the
            # one that goes unavailable, and the next read of it decides.
            _LOGGER.debug(
                "A read of %s on device ID %d on gateway %s did not answer; the "
                "rest of the device is untouched",
                entity.desc.key,
                device_id,
                self,
            )
        raise ModbusNoResponseError(f"Device ID {device_id} {reason}", partial=data)

    async def _probe_for_return(
        self,
        entities: list[ModbusContext],
        outage: _Outage,
        policy: DevicePolicy | None,
        data: dict[str, ModbusPDU],
        cache: dict[ReadKey, ModbusPDU],
        max_read_size: int,
    ) -> ModbusContext | None:
        """Ask a device that is backing off whether it is back.

        Returns the entity the probe read, so the poll that follows does not read
        it again, or `None` when this poll is not the one that asks and nothing was
        read at all. Raises `ModbusNoResponseError` when the probe does not come
        back with something usable: the device is not back yet, and there is nothing
        in this poll to give.

        A read of one entity says nothing about whether the device is back, so it is
        the routine refresh that brings a device back, and only a refresh that
        covers the whole device. The lock is what makes it the only one: every way
        of asking a device for a value comes through here, so a shared refresh and
        an entity on its own scan_interval cannot both ask the same device at once.
        """
        device_id: int = entities[0].device_id
        expected_offline: bool = policy.expected_offline if policy else False
        if not (policy.whole_device if policy else True):
            _LOGGER.debug(
                "Device ID %d on gateway %s is not answering; a read of one entity "
                "is left to the refresh of the whole device",
                device_id,
                self,
            )
            return None
        if not outage.due:
            _LOGGER.debug(
                "Device ID %d on gateway %s is not due a probe for another %d s",
                device_id,
                self,
                int(outage.next_probe - monotonic()),
            )
            return None

        # Due, so this poll is the one that asks. The entity the device nominates
        # for the purpose is read first, because a device that is still off is then
        # found on the cheapest register there is, and because one answer is enough
        # to know it is back. The rest of the device is read as normal afterwards,
        # so a device that is back is not left with one fresh value and the rest of
        # its entities waiting for their own timers.
        probe = self._probe_entity(entities, policy)
        _LOGGER.debug(
            "Probing device ID %d on gateway %s with %s",
            device_id,
            self,
            probe.desc.key,
        )
        if not await self._process_entity(probe, data, max_read_size, cache):
            self._note_gone(
                device_id, "no response to a recovery probe", expected_offline
            )
            raise ModbusNoResponseError(
                f"Device ID {device_id} did not answer a recovery probe with "
                f"{probe.desc.key}",
                partial=data,
            )
        if not data:
            # An answer that came back but could not be used is not proof of
            # recovery: a device coming up mid-read can answer before its registers
            # mean anything.
            self._note_gone(
                device_id,
                "no usable answer to a recovery probe",
                expected_offline,
            )
            raise ModbusNoResponseError(
                f"Device ID {device_id} answered a recovery probe with "
                f"{probe.desc.key} with nothing usable",
                partial=data,
            )
        self._note_answering(device_id)
        return probe

    def _probe_entity(
        self, entities: list[ModbusContext], policy: DevicePolicy | None
    ) -> ModbusContext:
        """The entity a recovery probe reads.

        The one the device's own configuration nominates, so a device whose first
        entity is an expensive read, or one that answers slowly while it is waking
        up, is asked something it answers as long as it is powered at all. Without
        a name the first entity of the poll is used, and so is the first entity
        when a refresh does not cover the one that was named.
        """
        probe_key: str | None = policy.probe_key if policy else None
        return next(
            (entity for entity in entities if entity.desc.key == probe_key), entities[0]
        )

    def _report_unusable(
        self, asked: list[ModbusContext], data: dict[str, ModbusPDU]
    ) -> None:
        """Warn about a device that answered some of this cycle and not others.

        The device is on the bus and talking, which is what separates this from a
        device that is off: it answers some registers and not others, so the values
        that do come back are worth having while the ones that do not are a fault
        worth looking at. One warning per cycle, naming what was missed - a line per
        entity would bury the fault in the entities it affects.
        """
        missing: list[str] = [
            entity.desc.key for entity in asked if entity.desc.key not in data
        ]
        if not missing:
            return
        _LOGGER.warning(
            "Device ID %d answered %d of the %d registers asked for this poll; no "
            "usable response for %s (connection resynchronised %d time(s))",
            asked[0].device_id,
            len(data),
            len(asked),
            ", ".join(missing),
            self._resyncs,
        )

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

        except ModbusIOException, ConnectionException, TimeoutError:
            # pymodbus raises these only after a device has failed to answer, so
            # this is the one case that says the device is no longer there. The
            # caller reports that once, as a change of state: a device that stays
            # away is polled every cycle, and a line per cycle is a line every few
            # seconds for as long as it is off.
            self._resync_transport()
            self._flag_desync()
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
