"""Test the gateway client for Modbus RTU over a serial proxy port."""
# pylint: disable=unexpected-keyword-arg, protected-access

import asyncio
import errno
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pymodbus.framer.rtu import FramerRTU
from pymodbus.transport import CommType
from pymodbus.transport.serialtransport import (
    create_serial_connection as pymodbus_create_serial_connection,
)
import pytest

from custom_components.modbus_local_gateway import serial_proxy
from custom_components.modbus_local_gateway.const import (
    SERIAL_DEFAULT_BAUDRATE,
    SERIAL_DEFAULT_BYTESIZE,
    SERIAL_DEFAULT_PARITY,
    SERIAL_DEFAULT_STOPBITS,
)
from custom_components.modbus_local_gateway.serial_client import (
    AsyncModbusSerialProxyClientGateway,
)
from custom_components.modbus_local_gateway.tcp_client import GatewayClient
from custom_components.modbus_local_gateway.transaction import MyTransactionManager

# A serial proxy URL as the ESPHome integration hands it out: the config entry
# of the adopted device, and the name of the proxy port on it.
URL: str = "esphome-hass://esphome/abc123?port_name=uart0"


def _client(**kwargs: Any) -> AsyncModbusSerialProxyClientGateway:
    """A client for the proxy port these tests talk to."""
    return AsyncModbusSerialProxyClientGateway(URL, **kwargs)


def _open_transport() -> Any:
    """A transport as pymodbus holds one while a connection is open."""
    transport = MagicMock()
    transport.wait_closed = AsyncMock()
    return transport


@pytest.mark.asyncio
async def test_describes_the_port_for_pymodbus() -> None:
    """The port is described with the UART settings the entry carries"""
    client = _client(baudrate=19200, bytesize=7, parity="E", stopbits=2)

    params = client.ctx.comm_params
    assert params.comm_type is CommType.SERIAL
    assert params.host == URL
    assert (params.baudrate, params.bytesize, params.parity, params.stopbits) == (
        19200,
        7,
        "E",
        2,
    )
    assert params.timeout_connect == 3.0
    # Never retried: a replayed write may reach the device twice when all that
    # went missing was its answer.
    assert client.ctx.retries == 0
    assert isinstance(client.ctx, MyTransactionManager)
    assert isinstance(client.ctx.framer, FramerRTU)
    # pymodbus types call_create as a plain callable, not as the partial it is.
    call_create: Any = client.ctx.call_create
    assert call_create.func is serial_proxy.create_serial_connection
    assert not client.connected


@pytest.mark.asyncio
async def test_defaults_are_the_ones_the_flow_stores() -> None:
    """Without settings of its own the port opens at the flow's defaults"""
    params = _client().ctx.comm_params
    assert params.baudrate == SERIAL_DEFAULT_BAUDRATE
    assert params.bytesize == SERIAL_DEFAULT_BYTESIZE
    assert params.parity == SERIAL_DEFAULT_PARITY
    assert params.stopbits == SERIAL_DEFAULT_STOPBITS
    assert params.timeout_connect == 3.0


@pytest.mark.asyncio
async def test_a_local_serial_port_is_left_to_pymodbus() -> None:
    """A serial URL that is no proxy port is pyserial's to open"""
    client = AsyncModbusSerialProxyClientGateway("/dev/ttyUSB0")

    call_create: Any = client.ctx.call_create
    assert call_create.func is pymodbus_create_serial_connection


@pytest.mark.asyncio
async def test_connect_does_nothing_while_the_port_is_open() -> None:
    """A client that is connected does not open the port a second time"""
    client = _client()
    release = _open_transport()
    client.ctx.transport = release
    client._closing = release

    with patch(
        "pymodbus.transport.transport.ModbusProtocol.connect",
        new_callable=AsyncMock,
    ) as open_port:
        assert await client.connect() is True

    open_port.assert_not_awaited()
    release.wait_closed.assert_not_awaited()
    assert client._closing is release


@pytest.mark.asyncio
async def test_connect_waits_for_the_last_connection_to_let_go() -> None:
    """The port is only opened once the connection that held it released it"""
    release = _open_transport()
    with patch(
        "custom_components.modbus_local_gateway.serial_proxy.create_serial_connection",
        new_callable=AsyncMock,
    ) as open_port:
        open_port.return_value = (MagicMock(), MagicMock())
        client = _client()
        client._closing = release

        assert await client.connect() is True

    release.wait_closed.assert_awaited_once()
    assert client._closing is None
    assert client.connected is True
    open_port.assert_awaited_once_with(
        client.ctx.loop,
        client.ctx.handle_new_connection,
        URL,
        baudrate=SERIAL_DEFAULT_BAUDRATE,
        bytesize=SERIAL_DEFAULT_BYTESIZE,
        parity=SERIAL_DEFAULT_PARITY,
        stopbits=SERIAL_DEFAULT_STOPBITS,
        timeout=3.0,
    )


@pytest.mark.asyncio
async def test_a_stuck_port_does_not_hold_up_the_reconnect() -> None:
    """Waiting for the release is bounded, so a stuck port cannot stall it"""
    closed: list[bool] = []

    async def never_closes() -> None:
        """A port that stays busy for longer than the wait allows."""
        closed.append(True)
        await asyncio.sleep(10)

    release: Any = MagicMock()
    release.wait_closed = never_closes
    with (
        patch(
            "custom_components.modbus_local_gateway.serial_proxy."
            "create_serial_connection",
            new_callable=AsyncMock,
        ) as open_port,
        patch(
            "custom_components.modbus_local_gateway.serial_client.RELEASE_TIMEOUT",
            0.01,
        ),
    ):
        open_port.return_value = (MagicMock(), MagicMock())
        client = _client()
        client._closing = release

        assert await client.connect() is True

    assert closed == [True]
    assert client._closing is None


@pytest.mark.asyncio
async def test_a_release_that_complains_does_not_stop_the_reconnect() -> None:
    """An error while closing is the port's own business, not the connect's"""

    async def fails_closing() -> None:
        """A port that reports how it went on the way down."""
        raise OSError(errno.EIO, "device went away")

    release: Any = MagicMock()
    release.wait_closed = fails_closing
    with patch(
        "custom_components.modbus_local_gateway.serial_proxy.create_serial_connection",
        new_callable=AsyncMock,
    ) as open_port:
        open_port.return_value = (MagicMock(), MagicMock())
        client = _client()
        client._closing = release

        assert await client.connect() is True

    assert client._closing is None


@pytest.mark.asyncio
async def test_close_keeps_the_transport_that_still_has_to_let_go() -> None:
    """The transport is held across the close, where only it knows the port"""
    client = _client()
    transport = _open_transport()
    client.ctx.transport = transport

    client.close()

    transport.close.assert_called_once()
    assert client._closing is transport
    assert client.ctx.transport is None
    assert not client.connected

    # Closing again has nothing left to hold on to and loses nothing either.
    client.close()
    assert client._closing is transport


@pytest.mark.asyncio
async def test_a_port_that_cannot_be_opened_reports_a_failed_connect() -> None:
    """A busy port comes back as a connect that did not happen, not a crash"""
    with patch(
        "custom_components.modbus_local_gateway.serial_proxy.create_serial_connection",
        new_callable=AsyncMock,
    ) as open_port:
        open_port.side_effect = OSError(errno.EBUSY, "Serial proxy port is busy")
        client = _client()

        assert await client.connect() is False

    assert not client.connected


@pytest.mark.asyncio
async def test_one_connection_is_shared_per_port() -> None:
    """Two entries on one port share a connection; other ports have their own"""
    key = f"{URL}:rtu"
    other_url = URL.replace("uart0", "uart1")
    other_key = f"{other_url}:rtu"
    try:
        first = AsyncModbusSerialProxyClientGateway.async_get_client_connection(
            URL, "rtu"
        )
        again = AsyncModbusSerialProxyClientGateway.async_get_client_connection(
            URL, "rtu"
        )
        other = AsyncModbusSerialProxyClientGateway.async_get_client_connection(
            other_url, "rtu"
        )

        assert again is first
        assert other is not first
        assert first._cache_key == key
        assert GatewayClient._CLIENT[key] is first

        first.close_cached()

        assert key not in AsyncModbusSerialProxyClientGateway._CLIENT
        assert other_key in AsyncModbusSerialProxyClientGateway._CLIENT
    finally:
        GatewayClient._CLIENT.pop(key, None)
        GatewayClient._CLIENT.pop(other_key, None)


@pytest.mark.asyncio
async def test_the_cached_client_carries_its_settings() -> None:
    """The settings a port is cached under are the settings it opens with"""
    client = AsyncModbusSerialProxyClientGateway.async_get_client_connection(
        URL, "rtu", baudrate=19200, parity="E", stopbits=2, bytesize=7
    )
    try:
        params = client.ctx.comm_params
        assert (params.baudrate, params.bytesize, params.parity, params.stopbits) == (
            19200,
            7,
            "E",
            2,
        )
        assert isinstance(client.ctx.framer, FramerRTU)
    finally:
        GatewayClient._CLIENT.pop(client._cache_key, None)
