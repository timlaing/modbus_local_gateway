"""Gateway client for Modbus RTU over a serial proxy port.

A serial proxy port - a UART of the Home Assistant Connect AUX-2, adopted
through ESPHome - is opened through the ``serialx`` transport the ESPHome
integration registers for it, not through pyserial: `serial_proxy` owns the
URL, what it means and what its failures look like, and this module is only
the client around that, with the two things the port itself insists on.

Everything that is the same for every gateway - reading, writing, polling,
the connection handling around them - is inherited from `GatewayClient`,
which does not know or care which way the bytes travel.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Protocol, cast

from pymodbus.client import ModbusBaseClient
from pymodbus.framer import FramerType
from pymodbus.transport import CommParams, CommType

from .const import (
    SERIAL_DEFAULT_BAUDRATE,
    SERIAL_DEFAULT_BYTESIZE,
    SERIAL_DEFAULT_PARITY,
    SERIAL_DEFAULT_STOPBITS,
)
from .serial_proxy import RELEASE_TIMEOUT
from .tcp_client import GatewayClient

_LOGGER: logging.Logger = logging.getLogger(__name__)


class _Releasable(Protocol):
    """A connection that can say when it has let go of the port."""

    async def wait_closed(self) -> None:
        """Return once the port is closed, or raise if it complains on the way."""


class AsyncModbusSerialProxyClientGateway(GatewayClient, ModbusBaseClient):
    """A gateway reached through a serial proxy port, speaking Modbus RTU.

    The port is exclusive, and that is what this adds to the shared client:
    a connection is only opened once the last one has let go of the port,
    because a proxy port refuses an opener that arrives while it is still
    closing, and a request is never retried, because a replayed write may
    reach the device twice when all that went missing was the answer.
    """

    def __init__(
        self,
        url: str,
        *,
        framer: FramerType = FramerType.RTU,
        baudrate: int = SERIAL_DEFAULT_BAUDRATE,
        bytesize: int = SERIAL_DEFAULT_BYTESIZE,
        parity: str = SERIAL_DEFAULT_PARITY,
        stopbits: int = SERIAL_DEFAULT_STOPBITS,
        timeout: float = 3.0,
        retries: int = 0,
    ) -> None:
        """Describe one serial proxy port to pymodbus, then set up the rest.

        The URL is everything the connection needs: the ESPHome integration
        gave it out for the port, it names the adopted device and the port on
        it, and the bytes ride the ESPHome connection Home Assistant already
        authenticated. Nothing is stored about the device itself, and no
        second connection to it is made.

        `retries` stays at zero. A retry is the same request sent again, and
        after a write whose answer went missing it is a second write whose
        first may have been applied - which Modbus cannot be asked about
        afterwards. A lost answer is reported as one instead.
        """
        # The transport of the connection that was closed, if its release has
        # not been waited for yet. It is gone from pymodbus the moment it is
        # closed, so it is kept here, where only the port's own transport can
        # say when the port is free again.
        self._closing: _Releasable | None = None
        comm_params = CommParams(
            comm_type=CommType.SERIAL,
            host=url,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            reconnect_delay=0.1,
            reconnect_delay_max=300,
            timeout_connect=timeout,
        )
        super().__init__(framer, retries, comm_params, None, None, None)

    async def connect(self) -> bool:
        """Open the port, waiting for the last connection to let go of it.

        A proxy port belongs to whoever holds it and reports a second opener
        as busy, whether or not the first has finished closing. So the
        connection that was closed is awaited before this one is made; the
        wait is bounded, because a port that never reports closed would
        otherwise hold every reconnect for as long as it liked.
        """
        if self.connected:
            return True
        await self._await_release()
        return await super().connect()

    def close(self) -> None:
        """Close this connection, remembering what still has to be released.

        pymodbus drops the transport as soon as it is closed, so it is held
        here before that happens: it is the only thing that can say when the
        port is free, and `connect` waits for it.
        """
        transport = cast("_Releasable | None", getattr(self.ctx, "transport", None))
        super().close()
        if transport is not None:
            self._closing = transport

    @classmethod
    def async_get_client_connection(
        cls,
        url: str,
        connection_type: str,
        *,
        baudrate: int = SERIAL_DEFAULT_BAUDRATE,
        bytesize: int = SERIAL_DEFAULT_BYTESIZE,
        parity: str = SERIAL_DEFAULT_PARITY,
        stopbits: int = SERIAL_DEFAULT_STOPBITS,
    ) -> AsyncModbusSerialProxyClientGateway:
        """Get the one client for this proxy port, making it the first time.

        Cached under the port and the framer, like the network client, so
        entries that point at the same port share one connection - which they
        have to anyway: the port can only be held once, and the two would
        otherwise take turns stealing it from each other.
        """
        key: str = f"{url}:{connection_type}"

        if key not in cls._CLIENT:
            _LOGGER.debug("Connecting to serial proxy port %s", key)
            client = cls(
                url,
                framer=FramerType(connection_type),
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
            )
            client._cache_key = key
            cls._CLIENT[key] = client
        # Only proxy ports are ever cached under a URL key, so what comes back
        # out of the cache is one of these.
        return cast(AsyncModbusSerialProxyClientGateway, cls._CLIENT[key])

    async def _await_release(self) -> None:
        """Wait for the port of a closed connection to be free again.

        Bounded by the same limit the config flow gives a probe, and silent:
        a port that takes too long or complains on the way down is still
        closing, and the open that follows says whether it got there.
        """
        transport, self._closing = self._closing, None
        if transport is None:
            return
        try:
            await asyncio.wait_for(transport.wait_closed(), RELEASE_TIMEOUT)
        except TimeoutError:
            _LOGGER.debug(
                "Serial proxy port did not report closed within %.0f s",
                RELEASE_TIMEOUT,
            )
        except OSError as err:
            _LOGGER.debug("Serial proxy port reported %s while closing", err)
