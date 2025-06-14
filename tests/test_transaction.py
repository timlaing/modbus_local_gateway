"""Test the MyTransactionManager class."""

# pylint: disable=unexpected-keyword-arg, protected-access
from asyncio import InvalidStateError
from unittest.mock import MagicMock, patch

import pytest
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu.pdu import ModbusPDU

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
        "custom_components.modbus_local_gateway.transaction.TransactionManager.data_received"
    ) as data_rec:
        data_rec.side_effect = ModbusIOException()
        rv = client.ctx.data_received(b"123")
        assert rv is None
        data_rec.assert_called_once()


@pytest.mark.asyncio
async def test_data_received_error_state() -> None:
    """Test the case when an IO error occurs"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    with patch(
        "custom_components.modbus_local_gateway.transaction.TransactionManager.data_received"
    ) as data_rec:
        data_rec.side_effect = InvalidStateError()
        rv = client.ctx.data_received(b"123")
        assert rv is None
        data_rec.assert_called_once()


@pytest.mark.asyncio
async def test_data_received() -> None:
    """Test normal data reception without errors"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    with patch(
        "custom_components.modbus_local_gateway.transaction.TransactionManager.data_received"
    ) as data_rec:
        rv = client.ctx.data_received(b"123")
        assert rv is None
        data_rec.assert_called_once()
