"""Serial proxy ports exposed by devices adopted through ESPHome.

The ESPHome ``serial_proxy`` component publishes a UART of an adopted device -
Home Assistant Connect AUX-2 has two - as a serial port. The ESPHome
integration registers those ports with the ``usb`` integration's serial scan and
a ``serialx`` transport that rides the ESPHome connection it already
authenticates, so nothing here opens a second connection or stores credentials:
the URL handed out by the scan is all that is needed.

Three things live here, and they are the only place that knows about the proxy:

- discovery, for the config flow to offer devices and their ports;
- validation, to answer "can this port be acquired with these settings" before
  anything is stored;
- the byte stream factory the Modbus RTU transport is built on.

The ports are identified by their URL, which carries the ESPHome config entry
and the name of the proxy, and by the serial number Home Assistant derives from
the device's MAC address and the port name, which is what stays the same when
Home Assistant is reinstalled.
"""

# serialx and the usb scan are imported where they are used, because neither is
# guaranteed to be there: a Home Assistant without the requirements or without
# the ESPHome integration has to still import this module to say so.
# pylint: disable=import-outside-toplevel

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
import errno
import importlib.util
import logging
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qs, urlparse

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN_ESPHOME, SERIAL_PORT_SCHEME

if TYPE_CHECKING:
    from homeassistant.components.usb import SerialDevice
    from serialx import Parity, StopBits

_LOGGER: logging.Logger = logging.getLogger(__name__)

# How long a port may take to come up. The ESPHome transport budgets its own
# connect at ten seconds; this is the outer bound for the flow's probe, which
# the user is waiting on.
PROBE_TIMEOUT: float = 15.0

# How long a released port is waited for before it is given up on. A port that
# never reports closed would otherwise hold up an unload or a reconnect.
RELEASE_TIMEOUT: float = 5.0

# What a failed probe is reported as in the config flow, by what went wrong.
BUSY = "port_busy"
CANNOT_CONNECT = "cannot_connect"
UNSUPPORTED = "unsupported_settings"
UNAVAILABLE = "serial_support_unavailable"

# What an error message has to say to be read as one of those, for the
# failures serialx reports as text rather than as a type: the device answers
# "not supported" and "invalid" for settings it cannot do, and the transport
# is missing altogether when no handler is registered for the scheme.
_UNSUPPORTED_WORDS = ("not supported", "invalid")
_UNAVAILABLE_WORDS = ("handler registered", "uri scheme")
_BUSY_WORDS = ("in use", "busy", "exclusive")


class SerialSupportUnavailable(Exception):
    """The libraries or integrations serial proxy ports need are not there."""

    def __init__(self, reason: str) -> None:
        """Remember what is missing, named as the flow reports it."""
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, kw_only=True)
class ProxyPort:
    """One serial proxy port, and how to talk about it in a form."""

    # The port as it is stored and opened: the canonical serialx URL.
    url: str
    # Stable across reinstalls: MAC address of the device plus the port name.
    serial_number: str
    # The ESPHome config entry the device behind this port is adopted as.
    entry_id: str
    # The `name` the port's `serial_proxy` is configured with.
    port_name: str
    # What the device is called in Home Assistant, for the device step.
    device_name: str
    # What the port is called next to the others of that device.
    port_label: str


def serialx_available() -> bool:
    """Whether the library that speaks to serial proxy ports is installed.

    Home Assistant installs it from the manifest before setting the
    integration up, so this being false means an installation that skipped
    requirements - which is why AUX-2 is offered only when it is there, rather
    than the whole integration failing to import.
    """
    try:
        return importlib.util.find_spec("serialx") is not None
    except ImportError, ValueError:  # pragma: no cover - no spec to find
        return False


async def async_get_proxy_ports(hass: HomeAssistant) -> list[ProxyPort]:
    """Return every serial proxy port Home Assistant can see, sorted for a form.

    Raises `SerialSupportUnavailable` when the ports cannot be looked up at
    all, which is a different problem from there being none: the first is a
    missing library or integration, the second is a device that has not been
    adopted yet.
    """
    reason = _support_reason(hass)
    if reason is not None:
        raise SerialSupportUnavailable(reason)

    from homeassistant.components import usb

    ports: list[ProxyPort] = []
    scanned: Sequence[SerialDevice] = await usb.async_scan_serial_ports(hass)
    for device in scanned:
        if not device.device.startswith(SERIAL_PORT_SCHEME):
            # Only proxy ports: a local /dev/tty device is a different
            # integration's port, and this gateway is about AUX-2.
            continue
        ports.append(_proxy_port(hass, device))
    return sorted(ports, key=lambda port: (port.device_name, port.port_label))


async def async_validate_port(
    hass: HomeAssistant, port: ProxyPort, **settings: Any
) -> str | None:
    """Return what the config flow shows when `port` cannot be used, or None.

    The only honest way to find out whether a proxy port exists, is free and
    takes these settings is to try to acquire it: the device reports an
    unsupported baud rate, a parity it cannot do and a port somebody else is
    holding when the port is opened, and nowhere before that. So the port is
    opened and released again, and nothing is stored while it is held.
    """
    del hass  # The URL resolves the connection itself; no handle is needed here.
    if not serialx_available():
        return UNAVAILABLE

    from serialx import SerialException, UnsupportedSetting, open_serial_connection

    writer: Any | None = None
    try:
        async with asyncio.timeout(PROBE_TIMEOUT):
            _reader, writer = await open_serial_connection(port.url, **settings)
    except UnsupportedSetting:
        return UNSUPPORTED
    except TimeoutError:
        return CANNOT_CONNECT
    except OSError as err:
        return BUSY if err.errno == errno.EBUSY else CANNOT_CONNECT
    except SerialException as err:
        return _probe_failure(err)

    await _release(writer)
    return None


async def create_serial_connection(
    loop: asyncio.AbstractEventLoop,
    protocol_factory: Callable[[], asyncio.BaseProtocol],
    url: str,
    *,
    baudrate: int,
    bytesize: int,
    parity: str,
    stopbits: int,
    timeout: float | None = None,
) -> tuple[asyncio.Transport, asyncio.BaseProtocol]:
    """Open `url` as an asyncio transport for `protocol_factory`.

    This is what the transaction manager is pointed at instead of pyserial,
    which knows nothing about a proxy URL. Every failure is an `OSError`,
    because that is what the transport layer treats as "not connected" - a
    busy port, a device that went away and a library that is not installed all
    end the same way there, and each of them says why in its message.

    `timeout` is the pymodbus connect budget, passed on to every transport
    factory there is. It is not passed on here: the ESPHome transport times
    its own connect out, and the outer `asyncio.wait_for` around this call
    cancels it well before the request timeout would matter.
    """
    del timeout
    if not serialx_available():
        raise OSError(errno.ENODEV, f"serialx is not installed; cannot open {url}")

    from serialx import SerialException, UnsupportedSetting
    from serialx import create_serial_connection as _open

    try:
        parity_value, stopbits_value = _uart_settings(parity, stopbits)
        return await _open(
            loop,
            cast("Callable[[], asyncio.Protocol]", protocol_factory),
            url,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity_value,
            stopbits=stopbits_value,
        )
    except UnsupportedSetting as err:
        raise OSError(
            errno.EINVAL, f"serial proxy port {url} rejects these settings: {err}"
        ) from err
    except ValueError as err:
        # A setting serialx has no name for - a parity the entry was edited to
        # carry - is refused the same way as one the device will not take.
        raise OSError(
            errno.EINVAL, f"serial proxy port {url} rejects these settings: {err}"
        ) from err
    except SerialException as err:
        raise OSError(
            errno.EIO, f"serial proxy port {url} could not be opened: {err}"
        ) from err


def _uart_settings(parity: str, stopbits: int) -> tuple[Parity, StopBits]:
    """Name the parity and the stop bits the way serialx spells them.

    A value the entry was edited to carry and serialx has no name for raises
    `ValueError`, which `create_serial_connection` refuses the same way as a
    setting the device itself will not take.
    """
    from serialx import Parity, StopBits

    return Parity(parity), StopBits(stopbits)


def _probe_failure(err: Exception) -> str:
    """Name what a refused probe means, for the config flow to show."""
    message = str(err).lower()
    if any(word in message for word in _BUSY_WORDS):
        return BUSY
    if any(word in message for word in _UNSUPPORTED_WORDS):
        return UNSUPPORTED
    if any(word in message for word in _UNAVAILABLE_WORDS):
        # The transport itself is not registered: the ESPHome integration is
        # there but has not published its serialx scheme, which is a missing
        # piece of setup rather than a port that will not answer.
        return UNAVAILABLE
    _LOGGER.debug("Serial proxy port refused the probe: %s", err)
    return CANNOT_CONNECT


async def _release(writer: Any) -> None:
    """Close a port opened for a probe and wait for it to be free again.

    Bounded, because a port that never reports closed would otherwise hold up
    the flow for as long as it liked.
    """
    # A port that refuses to close is not a failure of the probe: it was
    # opened, and whether it goes away again is what the wait below measures.
    with suppress(Exception):
        writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), RELEASE_TIMEOUT)
    except TimeoutError:
        _LOGGER.debug(
            "Serial proxy port did not report closed within %.0f s", RELEASE_TIMEOUT
        )
    except OSError as err:
        _LOGGER.debug("Serial proxy port reported %s while closing", err)


def _support_reason(hass: HomeAssistant) -> str | None:
    """Return what makes proxy ports unavailable, or None when they can be read."""
    if not serialx_available():
        return UNAVAILABLE
    if DOMAIN_ESPHOME not in hass.config.components:
        # No ESPHome device is adopted, so there is nothing to proxy. Said as
        # "no devices" rather than as a missing integration: the user has to
        # adopt the AUX-2 first either way.
        return None
    from homeassistant.components import usb

    if (
        not hasattr(usb, "async_scan_serial_ports")
        or "usb" not in hass.config.components
    ):
        # A Home Assistant old enough not to scan proxy ports, or one that runs
        # without the usb integration this scan is served by.
        return UNAVAILABLE
    return None


def _proxy_port(hass: HomeAssistant, device: SerialDevice) -> ProxyPort:
    """Describe one scanned proxy port for a form and for storage."""
    entry_id, port_name = _parse_url(device.device)
    entry: ConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
    device_name = _device_name(hass, entry, entry_id, device.description, port_name)
    port_type = _port_type(entry, port_name)
    return ProxyPort(
        url=device.device,
        serial_number=device.serial_number or f"{entry_id}-{port_name}",
        entry_id=entry_id,
        port_name=port_name,
        device_name=device_name,
        port_label=f"{port_name} ({port_type})" if port_type else port_name,
    )


def _parse_url(url: str) -> tuple[str, str]:
    """Return the ESPHome entry and the proxy port name a URL names."""
    parsed = urlparse(url)
    entry_id = parsed.path.strip("/")
    port_names = parse_qs(parsed.query).get("port_name", [""])
    return entry_id, port_names[0]


def _device_name(
    hass: HomeAssistant,
    entry: ConfigEntry | None,
    entry_id: str,
    description: str | None,
    port_name: str,
) -> str:
    """Return what the device behind a port is called in Home Assistant.

    The ESPHome entry is titled with the device's own name, which is what a
    user knows it by. When it is gone - the entry was removed while the scan
    still holds the port - the scan's description is the next best thing, and
    after that the port itself, so the form never has an empty row.
    """
    if entry is not None and entry.domain == DOMAIN_ESPHOME and entry.title:
        return entry.title
    if description and description.endswith(f" ({port_name})"):
        return description[: -len(f" ({port_name})")]
    if description:
        return description
    return entry_id[:8]


def _port_type(entry: ConfigEntry | None, port_name: str) -> str | None:
    """Return the electrical type of one port (RS232, RS485, TTL), if known.

    Worth showing because AUX-2's ports are RS-232: an RS-485 bus behind one
    needs an adapter, and picking a port without seeing that is how that gets
    missed. Read from the loaded ESPHome device, so it is absent rather than
    wrong when the device is offline or too old to report it.
    """
    if entry is None or entry.domain != DOMAIN_ESPHOME:
        return None
    if entry.state is not ConfigEntryState.LOADED:
        return None
    device_info = getattr(entry.runtime_data, "device_info", None)
    proxies = getattr(device_info, "serial_proxies", None) or []
    port_types: dict[str, str] = {
        proxy.name: proxy.port_type.name if proxy.port_type else "" for proxy in proxies
    }
    return port_types.get(port_name) or None
