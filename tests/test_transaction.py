"""Test the MyTransactionManager class."""
# pylint: disable=unexpected-keyword-arg, protected-access

from asyncio import InvalidStateError
from typing import cast
from unittest.mock import MagicMock, patch

from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu.pdu import ModbusPDU
import pytest

from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)
from custom_components.modbus_local_gateway.transaction import MyTransactionManager


@pytest.mark.asyncio
async def test_pdu_send() -> None:
    """Test the pdu_send method of MyTransactionManager."""
    mock_transaction_manager = MyTransactionManager(
        params=MagicMock(),
        framer=MagicMock(),
        retries=3,
        is_server=False,
        trace_connect=None,
        trace_packet=None,
        trace_pdu=None,
    )
    mock_transaction_manager.recv_buffer = b"initial_data"
    mock_pdu = MagicMock(spec=ModbusPDU)
    mock_addr = ("127.0.0.1", 502)

    with patch(
        "custom_components.modbus_local_gateway.transaction.TransactionManager.pdu_send"
    ) as mock_super_pdu_send:
        mock_transaction_manager.pdu_send(mock_pdu, mock_addr)
        assert mock_transaction_manager.recv_buffer == b""
        mock_super_pdu_send.assert_called_once_with(mock_pdu, mock_addr)


@pytest.mark.asyncio
async def test_data_received_error() -> None:
    """Test the case when an IO error occurs"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    with patch(
        "custom_components.modbus_local_gateway.transaction."
        "TransactionManager.data_received"
    ) as data_rec:
        data_rec.side_effect = ModbusIOException()
        ctx = cast(MyTransactionManager, client.ctx)
        assert ctx.suppressed_errors == 0
        client.ctx.data_received(b"123")
        data_rec.assert_called_once()
        assert ctx.suppressed_errors == 1


@pytest.mark.asyncio
async def test_data_received_error_state() -> None:
    """Test the case when an IO error occurs"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    with patch(
        "custom_components.modbus_local_gateway.transaction."
        "TransactionManager.data_received"
    ) as data_rec:
        data_rec.side_effect = InvalidStateError()
        ctx = cast(MyTransactionManager, client.ctx)
        client.ctx.data_received(b"123")
        data_rec.assert_called_once()
        assert ctx.suppressed_errors == 1


@pytest.mark.asyncio
async def test_data_received() -> None:
    """Test normal data reception without errors"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    with patch(
        "custom_components.modbus_local_gateway.transaction."
        "TransactionManager.data_received"
    ) as data_rec:
        ctx = cast(MyTransactionManager, client.ctx)
        client.ctx.data_received(b"123")
        data_rec.assert_called_once()
        assert ctx.suppressed_errors == 0


def _socket_frame(
    tid: int, unit: int = 1, fc: int = 3, payload: bytes = b"\x02\x00\x2a"
) -> bytes:
    """A Modbus TCP frame as a gateway would put it on the wire."""
    length = 2 + len(payload)
    return (
        tid.to_bytes(2, "big")
        + b"\x00\x00"
        + length.to_bytes(2, "big")
        + bytes([unit, fc])
        + payload
    )


@pytest.mark.asyncio
async def test_callback_data_counts_a_frame_for_another_request() -> None:
    """A frame that answers a different request marks the gateway desynced"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    ctx = cast(MyTransactionManager, client.ctx)
    ctx.request_dev_id = 1
    ctx.request_transaction_id = 5

    ctx.callback_data(_socket_frame(tid=4))

    assert ctx.mismatched_frames == 1
    assert ctx.desynced
    ctx.clear_desync()
    assert ctx.mismatched_frames == 0
    assert not ctx.desynced


@pytest.mark.asyncio
async def test_callback_data_counts_a_frame_nobody_waited_for() -> None:
    """An answer with no request in flight marks the gateway desynced"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    ctx = cast(MyTransactionManager, client.ctx)
    ctx.request_dev_id = 1
    ctx.request_transaction_id = 5
    ctx.response_future.set_result(None)

    ctx.callback_data(_socket_frame(tid=5))

    assert ctx.unsolicited_frames == 1
    assert ctx.desynced


@pytest.mark.asyncio
async def test_callback_data_ignores_a_matched_frame() -> None:
    """The answer to the request in flight is not an anomaly"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    ctx = cast(MyTransactionManager, client.ctx)
    ctx.request_dev_id = 1
    ctx.request_transaction_id = 5

    ctx.callback_data(_socket_frame(tid=5))

    assert ctx.mismatched_frames == 0
    assert ctx.unsolicited_frames == 0
    assert not ctx.desynced
