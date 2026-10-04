"""The ways a read or a write against a gateway can go wrong."""

from pymodbus.exceptions import ModbusException
from pymodbus.pdu.pdu import ModbusPDU


class ModbusClientError(ModbusException):
    """Typed Modbus client error."""

    def __init__(self, string: str) -> None:
        """Initialize the error."""
        super().__init__(string)  # type: ignore[no-untyped-call]
        self.string = string


class ModbusNoResponseError(ModbusClientError):
    """A device stopped answering part way through a poll cycle.

    Nothing came back at all, which is a different thing from an answer that came
    back wrong: a protocol answer means the device is on the bus and talking, so a
    wrong length, an exception response or a stale answer is a question about the
    data rather than about the device being there.

    The cycle is abandoned at that point instead of asking every remaining entity
    of the device in turn. A device that has gone quiet costs one timeout sequence
    rather than one per entity, and the shared client lock is released as the error
    travels out, so the other devices behind the same gateway keep polling.
    """

    def __init__(
        self, string: str, partial: dict[str, ModbusPDU] | None = None
    ) -> None:
        """Initialize the error with what was read before the silence started."""
        super().__init__(string)
        self.partial: dict[str, ModbusPDU] = partial if partial is not None else {}
