"""TCP Client for Modbus Local Gateway"""

from asyncio import InvalidStateError
from typing import Any

from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.transaction import TransactionManager


class MyTransactionManager(TransactionManager):
    """Custom Transaction Manager to suppress exception logging"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the manager and start counting the frames it discards."""
        super().__init__(*args, **kwargs)
        # Frames the protocol was not expecting: a late answer to a request
        # that was already retried, or the tail of a frame the framer could
        # not decode. Counted rather than logged one by one, because a
        # TCP-to-RTU bridge under load produces them in bursts.
        self.suppressed_errors: int = 0
        # Frames that answered some request other than the one in flight.
        self.mismatched_frames: int = 0
        # Answers that arrived with no request waiting for them.
        self.unsolicited_frames: int = 0

    @property
    def desynced(self) -> bool:
        """Whether the gateway is answering out of request order.

        A gateway that bridges TCP to a shared serial bus that fell behind
        leaves an answer queued for a request that has already been given up
        on, and that answer turns up while the next request is waiting for its
        own. While this is true the connection is not in step with the bridge,
        and the only way to get back into step is to drop the queued answers.
        """
        return bool(self.mismatched_frames or self.unsolicited_frames)

    def clear_desync(self) -> None:
        """Forget the out-of-order answers seen so far.

        Called once the connection has been renewed, and after a read that came
        back matched. A match is not proof of which request produced the answer -
        over RTU-TCP there is no transaction id to match on - but it is enough
        to say the gateway is not still answering out of order.
        """
        self.mismatched_frames = 0
        self.unsolicited_frames = 0

    def data_received(self, data: bytes) -> None:
        """Catch any protocol exceptions so they don't pollute the HA logs"""
        try:
            super().data_received(data)
        except ModbusIOException, InvalidStateError:
            self.suppressed_errors += 1

    def callback_data(self, data: bytes, addr: tuple[str, int] | None = None) -> int:
        """Count the frames that do not belong to the request in flight."""
        self._count_out_of_order(data)
        return super().callback_data(data, addr)

    def _count_out_of_order(self, data: bytes) -> None:
        """Walk the received frames without changing how they are matched.

        pymodbus logs these frames as errors and skips them, but it does not
        report that it did: the client only finds out from the log, and from
        the log alone it cannot tell a gateway that is answering one request
        late from one that is answering a request nobody is waiting for. The
        same walk is done here, read-only, so the connection knows whether it
        is in step with the gateway.
        """
        offset: int = 0
        # One request has one answer, so a second frame that matches the request
        # in flight is an answer to something else even though the future for the
        # first has not been resolved yet.
        answered: bool = self.response_future.done()
        while offset < len(data):
            used_len, dev_id, tid, frame = self.framer.decode(data[offset:])
            if not used_len or not frame:
                return
            offset += used_len
            if (
                self.request_dev_id
                and dev_id != self.request_dev_id
                or self.request_transaction_id
                and tid
                and tid != self.request_transaction_id
            ):
                self.mismatched_frames += 1
            elif answered:
                self.unsolicited_frames += 1
            else:
                answered = True

    def pdu_send(self, pdu: ModbusPDU, addr: tuple[str, int] | None = None) -> None:
        """Initialize the recv buffer before each send to prevent duplication of data"""
        self.recv_buffer = b""
        return super().pdu_send(pdu, addr)
