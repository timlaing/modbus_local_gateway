"""TCP Client for Modbus Local Gateway"""

import contextlib

from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.transaction import TransactionManager


class MyTransactionManager(TransactionManager):
    """Custom Transaction Manager to supress exception logging"""

    def data_received(self, data: bytes) -> None:
        """Catch any protocol exceptions so they don't pollute the HA logs"""
        with contextlib.suppress(ModbusIOException):
            super().data_received(data)

    def pdu_send(self, pdu: ModbusPDU, addr: tuple | None = None) -> None:
        """Initialize the recv buffer before each send to prevent duplication of data"""
        self.recv_buffer = b""
        return super().pdu_send(pdu, addr)
