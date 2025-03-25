"""Tests for the Modbus Local Gateway config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import HomeAssistant, MockConfigEntry

from custom_components.modbus_local_gateway.config_flow import (
    ConfigFlowHandler,
    OptionsFlowHandler,
)
from custom_components.modbus_local_gateway.const import (
    CONF_PREFIX,
    CONF_SLAVE_ID,
    DOMAIN,
    OPTIONS_REFRESH,
)


@pytest.mark.asyncio
async def test_async_step_user(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Test the user step of the config flow."""
    flow = ConfigFlowHandler()
    flow.hass = hass

    with patch(
        "custom_components.modbus_local_gateway.config_flow.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=mock_client,
    ):
        result: ConfigFlowResult = await flow.async_step_user(
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: 502,
                CONF_SLAVE_ID: 1,
                CONF_PREFIX: "test",
            }
        )
        assert "type" in result
        assert "errors" in result
        assert result["type"] == "form"
        assert result["errors"] == {"base": "Gateway connection"}

        mock_client.connected = True
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: 502,
                CONF_SLAVE_ID: 1,
                CONF_PREFIX: "test",
            }
        )
        assert "type" in result
        assert "step_id" in result
        assert result["type"] == "form"
        assert result["step_id"] == "device_type"


@pytest.mark.asyncio
async def test_async_step_device_type(hass: HomeAssistant) -> None:
    """Test the device type step of the config flow."""
    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.data = {CONF_FILENAME: "test.yaml"}
    hass.data[DOMAIN] = {}

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {
            "test": {
                "name": "Title",
                "address": 1,
                "float": True,
                "string": False,
                "bits": 8,
                "shift_bits": 2,
                "multiplier": 10,
                "size": 4,
                "icon": "mdi:icon",
                "precision": 2,
                "map": {1: "One"},
                "state_class": "total",
                "device_class": "A",
                "unit_of_measurement": "%",
                "flags": {1: "One"},
            },
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with patch(
        "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml",
        return_value=_config,
    ) as load_devices:
        result: ConfigFlowResult = await flow.async_step_device_type(
            user_input=flow.data
        )
        assert "type" in result
        assert result["type"] == "create_entry"
        assert load_devices.called


@pytest.mark.asyncio
async def test_async_create(hass: HomeAssistant) -> None:
    """Test the create step of the config flow."""
    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.data = {CONF_FILENAME: "test.yaml"}

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        return_value=MagicMock(manufacturer="Test", model="Device"),
    ):
        result: ConfigFlowResult = await flow.async_create()
        assert "type" in result
        assert "title" in result
        assert result["type"] == "create_entry"
        assert result["title"] == "Test Device"


@pytest.mark.asyncio
async def test_async_abort(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Test the abort step of the config flow."""
    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.client = mock_client

    result: ConfigFlowResult = flow.async_abort(reason="test")
    assert "type" in result
    assert result["type"] == "abort"
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_show_progress_done(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """Test the show progress done step of the config flow."""
    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.client = mock_client

    result: ConfigFlowResult = flow.async_show_progress_done(next_step_id="test")
    assert "type" in result
    assert result["type"] == "progress_done"
    mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_options_flow_handler(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the options flow handler."""
    mock_config_entry.add_to_hass(hass)
    flow = OptionsFlowHandler()
    flow.hass = hass
    flow.handler = mock_config_entry.entry_id
    hass.data = {DOMAIN: {"localhost:123:1": MagicMock()}}  # type: ignore

    result: ConfigFlowResult = await flow.async_step_init(
        user_input={OPTIONS_REFRESH: 10}
    )
    assert "type" in result
    assert "data" in result
    assert result["type"] == "create_entry"
    assert result["data"] == {OPTIONS_REFRESH: 10}

    result = await flow.async_step_init(user_input=None)
    assert "type" in result
    assert "step_id" in result
    assert result["type"] == "form"
    assert result["step_id"] == "init"
