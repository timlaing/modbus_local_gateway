"""Tests for the Modbus Local Gateway diagnostics."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
import pytest
from pytest_homeassistant_custom_component.common import HomeAssistant

from custom_components.modbus_local_gateway.const import (
    CONF_BAUDRATE,
    CONF_DEVICE,
    CONF_PARITY,
    CONF_SERIAL_NUMBER,
)
from custom_components.modbus_local_gateway.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import mock_gateway_entry, mock_serial_gateway_entry


@pytest.mark.asyncio
async def test_a_network_gateway_reports_its_settings(
    hass: HomeAssistant,
) -> None:
    """A report says how the gateway is reached, without saying where.

    The host is the one thing of it that should not be pasted into an
    issue; the port and the framer are what the connection is tried with,
    so they are kept.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["state"] == "not_loaded"
    assert diagnostics["transport"] == "network"
    assert diagnostics["connection_type"] == "socket"
    assert diagnostics["devices"] == 1
    assert diagnostics["settings"]["host"] == "**REDACTED**"
    assert diagnostics["settings"]["port"] == 123
    # The library question is one a serial gateway asks, not this one.
    assert "serial_support" not in diagnostics


@pytest.mark.asyncio
async def test_an_aux2_gateway_reports_its_uart_settings(
    hass: HomeAssistant,
) -> None:
    """A serial report says how the line is talked on, not which port.

    The UART settings are what a connection is refused over, so a report
    has to carry them; the port URL and the serial number identify the
    installation and are redacted.
    """
    entry = mock_serial_gateway_entry()
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.NOT_LOADED)

    with patch(
        "custom_components.modbus_local_gateway.diagnostics.serialx_available",
        return_value=True,
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["state"] == "not_loaded"
    assert diagnostics["transport"] == "serial_proxy"
    assert diagnostics["connection_type"] == "rtu"
    assert diagnostics["settings"][CONF_BAUDRATE] == 19200
    assert diagnostics["settings"][CONF_PARITY] == "E"
    assert diagnostics["settings"][CONF_DEVICE] == "**REDACTED**"
    assert diagnostics["settings"][CONF_SERIAL_NUMBER] == "**REDACTED**"
    assert diagnostics["serial_support"] is True
