"""Test the discovery, validation and opening of serial proxy ports."""
# pylint: disable=unexpected-keyword-arg, protected-access

import asyncio
import errno
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.usb import SerialDevice
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from serialx import Parity, SerialException, StopBits, UnsupportedSetting

from custom_components.modbus_local_gateway.const import (
    DOMAIN_ESPHOME,
    SERIAL_PORT_SCHEME,
)
from custom_components.modbus_local_gateway.serial_proxy import (
    BUSY,
    CANNOT_CONNECT,
    UNAVAILABLE,
    UNSUPPORTED,
    ProxyPort,
    SerialSupportUnavailable,
    async_get_proxy_ports,
    async_validate_port,
    create_serial_connection,
    serialx_available,
)

# A proxy port URL as the ESPHome integration hands it out: the config entry
# of the adopted device, and the name of the proxy port on it.
URL: str = "esphome-hass://esphome/abc123?port_name=uart0"


def _port(**overrides: Any) -> ProxyPort:
    """A proxy port as the config flow would hold it."""
    values: dict[str, Any] = {
        "url": URL,
        "serial_number": "aabbccddeeff-uart0",
        "entry_id": "abc123",
        "port_name": "uart0",
        "device_name": "Home Assistant Connect AUX-2",
        "port_label": "uart0",
    }
    values.update(overrides)
    return ProxyPort(**values)


def _scanned(device: str, **overrides: Any) -> SerialDevice:
    """A serial port as the scan reports it."""
    values: dict[str, Any] = {
        "device": device,
        "serial_number": "aabbccddeeff-uart0",
        "manufacturer": "Nabu Casa",
        "description": "Home Assistant Connect AUX-2 (uart0)",
    }
    values.update(overrides)
    return SerialDevice(**values)


@pytest.mark.asyncio
async def test_only_proxy_urls_are_offered(hass: HomeAssistant) -> None:
    """A local serial port belongs to another integration; only proxies count"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    scan = AsyncMock(
        return_value=[
            _scanned(
                "/dev/tty.usbserial-1420",
                serial_number="USB1",
                manufacturer=None,
                description="USB Serial",
            ),
            _scanned(
                f"{SERIAL_PORT_SCHEME}://esphome/abc123?port_name=uart1",
                serial_number="aabbccddeeff-uart1",
                description="Home Assistant Connect AUX-2 (uart1)",
            ),
        ]
    )
    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        ports = await async_get_proxy_ports(hass)

    assert [port.url for port in ports] == [
        "esphome-hass://esphome/abc123?port_name=uart1"
    ]
    port = ports[0]
    assert port.serial_number == "aabbccddeeff-uart1"
    assert port.entry_id == "abc123"
    assert port.port_name == "uart1"
    assert port.device_name == "Home Assistant Connect AUX-2"
    assert port.port_label == "uart1"


@pytest.mark.asyncio
async def test_ports_are_read_through_the_usb_scan(hass: HomeAssistant) -> None:
    """An adopted device with the usb scan running is a supported setup"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    scan = AsyncMock(return_value=[])

    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        assert await async_get_proxy_ports(hass) == []

    scan.assert_awaited_once()


@pytest.mark.asyncio
async def test_nothing_is_scanned_without_an_adopted_device(
    hass: HomeAssistant,
) -> None:
    """No adopted ESPHome device means no proxy ports and no scan to ask"""
    scan = AsyncMock(return_value=[])

    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        assert await async_get_proxy_ports(hass) == []

    # The scan needs a set-up usb integration that this fixture never had, so
    # it must not be reached: the missing device settles the answer first.
    scan.assert_not_awaited()


@pytest.mark.asyncio
async def test_ports_are_sorted_for_the_form(hass: HomeAssistant) -> None:
    """Devices come out in name order and their ports in port name order"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    scan = AsyncMock(
        return_value=[
            _scanned(
                f"{SERIAL_PORT_SCHEME}://esphome/bbb?port_name=uart1",
                description="Lab AUX (uart1)",
            ),
            _scanned(
                f"{SERIAL_PORT_SCHEME}://esphome/aaa?port_name=uart1",
                description="Attic AUX (uart1)",
            ),
            _scanned(
                f"{SERIAL_PORT_SCHEME}://esphome/aaa?port_name=uart0",
                description="Attic AUX (uart0)",
            ),
        ]
    )
    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        ports = await async_get_proxy_ports(hass)

    assert [(port.device_name, port.port_name) for port in ports] == [
        ("Attic AUX", "uart0"),
        ("Attic AUX", "uart1"),
        ("Lab AUX", "uart1"),
    ]


@pytest.mark.asyncio
async def test_a_loaded_device_names_its_ports(hass: HomeAssistant) -> None:
    """A loaded ESPHome entry names its device and says what a port is"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    entry = MockConfigEntry(
        domain=DOMAIN_ESPHOME,
        entry_id="abc123",
        title="Garage AUX-2",
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        device_info=SimpleNamespace(
            serial_proxies=[
                SimpleNamespace(name="uart0", port_type=SimpleNamespace(name="RS232"))
            ]
        )
    )
    scan = AsyncMock(return_value=[_scanned(URL, description=None)])

    try:
        with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
            ports = await async_get_proxy_ports(hass)

        port = ports[0]
        assert port.device_name == "Garage AUX-2"
        assert port.port_label == "uart0 (RS232)"
    finally:
        # Said to be unloaded again, so that teardown does not try to unload
        # a device integration this test environment never set up.
        entry.mock_state(hass, ConfigEntryState.NOT_LOADED)


@pytest.mark.asyncio
async def test_a_port_the_scan_says_little_about_still_gets_a_row(
    hass: HomeAssistant,
) -> None:
    """With no entry and no description the port still describes itself"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    url = f"{SERIAL_PORT_SCHEME}://esphome/deadbeef1234"
    scan = AsyncMock(return_value=[_scanned(url, serial_number=None, description=None)])

    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        ports = await async_get_proxy_ports(hass)

    port = ports[0]
    assert port.entry_id == "deadbeef1234"
    assert port.port_name == ""
    # No scan serial number: the entry and port name stand in for one.
    assert port.serial_number == "deadbeef1234-"
    assert port.device_name == "deadbeef"
    assert port.port_label == ""


@pytest.mark.asyncio
async def test_a_description_without_the_port_in_it_is_used_whole(
    hass: HomeAssistant,
) -> None:
    """A description that names only the device still says what it is"""
    hass.config.components.add(DOMAIN_ESPHOME)
    hass.config.components.add("usb")
    scan = AsyncMock(return_value=[_scanned(URL, description="Prolific Adapter")])

    with patch("homeassistant.components.usb.async_scan_serial_ports", scan):
        ports = await async_get_proxy_ports(hass)

    assert ports[0].device_name == "Prolific Adapter"


@pytest.mark.asyncio
async def test_ports_are_unavailable_without_the_usb_scan(
    hass: HomeAssistant,
) -> None:
    """With a device adopted but no scan to ask, the ports cannot be read"""
    hass.config.components.add(DOMAIN_ESPHOME)

    with pytest.raises(SerialSupportUnavailable) as err:
        await async_get_proxy_ports(hass)

    assert err.value.reason == UNAVAILABLE


@pytest.mark.asyncio
async def test_ports_are_unavailable_without_serialx(hass: HomeAssistant) -> None:
    """Without the library the ports open with, none can be offered"""
    with (
        patch(
            "custom_components.modbus_local_gateway.serial_proxy.serialx_available",
            return_value=False,
        ),
        pytest.raises(SerialSupportUnavailable) as err,
    ):
        await async_get_proxy_ports(hass)

    assert err.value.reason == UNAVAILABLE


def test_serialx_availability_follows_the_library() -> None:
    """The library missing is seen as such, without an error being raised"""
    assert serialx_available() is True
    with patch(
        "custom_components.modbus_local_gateway.serial_proxy.importlib.util.find_spec",
        return_value=None,
    ):
        assert serialx_available() is False


@pytest.mark.asyncio
async def test_a_port_is_acquired_and_handed_back(hass: HomeAssistant) -> None:
    """The probe opens the port with the chosen settings and lets go again"""
    writer: Any = MagicMock()
    writer.wait_closed = AsyncMock()
    open_port = AsyncMock(return_value=(MagicMock(), writer))

    with patch("serialx.open_serial_connection", open_port):
        result = await async_validate_port(
            hass, _port(), baudrate=19200, bytesize=7, parity="E", stopbits=2
        )

    assert result is None
    open_port.assert_awaited_once_with(
        URL, baudrate=19200, bytesize=7, parity="E", stopbits=2
    )
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited_once()


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (UnsupportedSetting("stopbits=2 is not possible"), UNSUPPORTED),
        (TimeoutError(), CANNOT_CONNECT),
        (OSError(errno.EBUSY, "Serial proxy port is already in use"), BUSY),
        (OSError(errno.ENODEV, "device not found"), CANNOT_CONNECT),
        (SerialException("Serial proxy port is already in use: uart0"), BUSY),
        (SerialException("invalid baud rate"), UNSUPPORTED),
        (SerialException("No handler registered for URI scheme"), UNAVAILABLE),
        (SerialException("connection reset by the device"), CANNOT_CONNECT),
    ],
)
@pytest.mark.asyncio
async def test_a_probe_that_refuses_says_why(
    hass: HomeAssistant, failure: Exception, expected: str
) -> None:
    """What refused the probe is what the flow is told to show"""
    with patch("serialx.open_serial_connection", new=AsyncMock(side_effect=failure)):
        assert await async_validate_port(hass, _port()) == expected


@pytest.mark.asyncio
async def test_a_probe_without_the_library_says_so(hass: HomeAssistant) -> None:
    """Without serialx the port cannot be probed, and that is what is shown"""
    with (
        patch(
            "custom_components.modbus_local_gateway.serial_proxy.serialx_available",
            return_value=False,
        ),
        patch("serialx.open_serial_connection", new_callable=AsyncMock) as open_port,
    ):
        assert await async_validate_port(hass, _port()) == UNAVAILABLE

    open_port.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_port_that_never_reports_closed_is_still_given_up(
    hass: HomeAssistant,
) -> None:
    """The wait for the probe's port to close is bounded"""
    writer: Any = MagicMock()

    async def never_closes() -> None:
        """A port that never says it is free again."""
        await asyncio.sleep(10)

    writer.wait_closed = never_closes
    with (
        patch(
            "serialx.open_serial_connection",
            new=AsyncMock(return_value=(MagicMock(), writer)),
        ),
        patch(
            "custom_components.modbus_local_gateway.serial_proxy.RELEASE_TIMEOUT",
            0.01,
        ),
    ):
        assert await async_validate_port(hass, _port()) is None


@pytest.mark.asyncio
async def test_a_port_that_complains_while_closing_is_still_left(
    hass: HomeAssistant,
) -> None:
    """An error while closing does not turn a good probe into a bad one"""
    writer: Any = MagicMock()

    async def fails_closing() -> None:
        """A port that reports an error on the way down."""
        raise OSError(errno.EIO, "device went away")

    writer.wait_closed = fails_closing
    with patch(
        "serialx.open_serial_connection",
        new=AsyncMock(return_value=(MagicMock(), writer)),
    ):
        assert await async_validate_port(hass, _port()) is None


@pytest.mark.asyncio
async def test_the_factory_hands_the_settings_to_serialx() -> None:
    """Everything the transport opens the port with reaches serialx"""
    transport: Any = MagicMock()
    protocol: Any = MagicMock()
    loop: Any = MagicMock()
    factory: Any = MagicMock()
    open_port = AsyncMock(return_value=(transport, protocol))

    with patch("serialx.create_serial_connection", open_port):
        result = await create_serial_connection(
            loop,
            factory,
            URL,
            baudrate=19200,
            bytesize=7,
            parity="E",
            stopbits=2,
        )

    assert result == (transport, protocol)
    # The pymodbus connect budget is not a setting of the port: the ESPHome
    # transport budgets its own connect, so no `timeout` is forwarded.
    open_port.assert_awaited_once_with(
        loop,
        factory,
        URL,
        baudrate=19200,
        bytesize=7,
        parity=Parity.EVEN,
        stopbits=StopBits.TWO,
    )


@pytest.mark.asyncio
@patch("serialx.create_serial_connection", new_callable=AsyncMock)
async def test_a_setting_serialx_has_no_name_for_is_refused(
    open_port: AsyncMock,
) -> None:
    """A parity the entry was edited to carry is refused as an OSError"""
    loop: Any = MagicMock()
    factory: Any = MagicMock()
    with pytest.raises(OSError) as err:
        await create_serial_connection(
            loop,
            factory,
            URL,
            baudrate=9600,
            bytesize=8,
            parity="X",
            stopbits=1,
        )

    assert err.value.errno == errno.EINVAL
    assert URL in str(err.value)
    open_port.assert_not_awaited()


@pytest.mark.parametrize(
    ("failure", "expected_errno"),
    [
        (UnsupportedSetting("stopbits=2 is not possible"), errno.EINVAL),
        (SerialException("connection reset by the device"), errno.EIO),
    ],
)
@pytest.mark.asyncio
@patch("serialx.create_serial_connection", new_callable=AsyncMock)
async def test_a_refused_open_comes_back_as_an_os_error(
    open_port: AsyncMock, failure: Exception, expected_errno: int
) -> None:
    """pymodbus reads OSError as "not connected", so that is what it gets"""
    open_port.side_effect = failure
    loop: Any = MagicMock()
    factory: Any = MagicMock()
    with pytest.raises(OSError) as err:
        await create_serial_connection(
            loop,
            factory,
            URL,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

    assert err.value.errno == expected_errno
    assert URL in str(err.value)


@pytest.mark.asyncio
@patch("serialx.create_serial_connection", new_callable=AsyncMock)
@patch(
    "custom_components.modbus_local_gateway.serial_proxy.serialx_available",
    return_value=False,
)
async def test_a_port_cannot_be_opened_without_the_library(
    available: MagicMock, open_port: AsyncMock
) -> None:
    """With serialx missing the open fails as an OSError, not an ImportError"""
    loop: Any = MagicMock()
    factory: Any = MagicMock()
    with pytest.raises(OSError) as err:
        await create_serial_connection(
            loop,
            factory,
            URL,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

    assert err.value.errno == errno.ENODEV
    available.assert_called_once_with()
    open_port.assert_not_awaited()
