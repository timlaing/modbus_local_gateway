"""Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    HomeAssistant,
    MockConfigEntry,
)

from custom_components.modbus_local_gateway import async_setup_entry, async_unload_entry
from custom_components.modbus_local_gateway.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            "slave_id": 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
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
    """Test the unload entry function."""
    hass.data = {"modbus_local_gateway": {"localhost:123:1": "coordinator"}}  # type: ignore[assignment]

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            "slave_id": 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
        },
    )

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock()
        ) as unload_patch,
    ):
        result: bool = await async_unload_entry(hass, mock_config_entry)
        assert result is True
        unload_patch.assert_awaited_once()
        assert "localhost:123:1" not in hass.data["modbus_local_gateway"]
