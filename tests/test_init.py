"""Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    HomeAssistant,
    MockConfigEntry,
)

from custom_components.modbus_local_gateway import async_setup_entry, async_unload_entry
from custom_components.modbus_local_gateway.const import CONF_DEVICE_ID, DOMAIN


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            CONF_DEVICE_ID: 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
            "connection_type": "socket",
        },
    )
    mock_config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ):
        await async_setup_entry(hass, mock_config_entry)

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            CONF_DEVICE_ID: 2,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
            "connection_type": "rtu",
        },
    )
    mock_config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        return_value=True,
    ):
        await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant) -> None:
    """Unloading the last entry on a gateway must close its client.

    Leaving it open keeps the socket - and pymodbus' retries - alive after the
    entry is gone, so a disabled entry carries on talking to the device.
    """
    coordinator = MagicMock()
    hass.data = {"modbus_local_gateway": {"test-localhost:123:1": coordinator}}  # type: ignore[assignment]

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            CONF_DEVICE_ID: 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
        },
    )

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock()
        ) as unload_patch,
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.close_client_connection"
        ) as close_patch,
    ):
        result: bool = await async_unload_entry(hass, mock_config_entry)
        assert result is True
        unload_patch.assert_awaited_once()
        assert "test-localhost:123:1" not in hass.data["modbus_local_gateway"]
        close_patch.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_shared_client(hass: HomeAssistant) -> None:
    """A client shared with another entry on the same gateway must stay open.

    One client is cached per host/port/framer, so two entries differing only by
    slave id share it. Closing it on the first unload would kill the second.
    """
    shared_client = MagicMock()
    leaving = MagicMock()
    leaving.client = shared_client
    staying = MagicMock()
    staying.client = shared_client
    hass.data = {  # type: ignore[assignment]
        "modbus_local_gateway": {
            "test-localhost:123:1": leaving,
            "test-localhost:123:2": staying,
        }
    }

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            CONF_DEVICE_ID: 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
        },
    )

    with (
        patch.object(hass.config_entries, "async_unload_platforms", AsyncMock()),
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.close_client_connection"
        ) as close_patch,
    ):
        assert await async_unload_entry(hass, mock_config_entry) is True
        assert "test-localhost:123:1" not in hass.data["modbus_local_gateway"]
        assert "test-localhost:123:2" in hass.data["modbus_local_gateway"]
        close_patch.assert_not_called()


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_state_when_platforms_fail(
    hass: HomeAssistant,
) -> None:
    """A failed platform unload must leave the entry intact.

    Entities are still loaded at that point, so closing the shared client would
    strand them on a dead connection - and returning True would tell Home
    Assistant the entry had gone.
    """
    coordinator = MagicMock()
    hass.data = {"modbus_local_gateway": {"test-localhost:123:1": coordinator}}  # type: ignore[assignment]

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            CONF_DEVICE_ID: 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
        },
    )

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=False),
        ),
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.close_client_connection"
        ) as close_patch,
    ):
        assert await async_unload_entry(hass, mock_config_entry) is False
        assert "test-localhost:123:1" in hass.data["modbus_local_gateway"]
        close_patch.assert_not_called()
