"""TCP Client for Modbus Local Gateway"""

from asyncio import InvalidStateError
from typing import Any

from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.transaction import TransactionManager


class MyTransactionManager(TransactionManager):
    """Custom Transaction Manager to suppress exception logging"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the manager and count the frames it had to discard."""
        super().__init__(*args, **kwargs)
        # Frames the protocol was not expecting: a late answer to a request
        # that was already retried, or the tail of a frame the framer could
        # not decode. Counted rather than logged one by one, because a
        # TCP-to-RTU bridge under load produces them in bursts.
        self.suppressed_errors: int = 0

    def data_received(self, data: bytes) -> None:
        """Catch any protocol exceptions so they don't pollute the HA logs"""
        try:
            super().data_received(data)
        except ModbusIOException, InvalidStateError:
            self.suppressed_errors += 1

    def pdu_send(self, pdu: ModbusPDU, addr: tuple[str, int] | None = None) -> None:
        """Initialize the recv buffer before each send to prevent duplication of data"""
        self.recv_buffer = b""
        return super().pdu_send(pdu, addr)
