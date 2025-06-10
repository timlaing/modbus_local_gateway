"""Sensor tests"""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import (
    HomeAssistant,
    MockConfigEntry,
)

from custom_components.modbus_local_gateway import async_setup_entry
from custom_components.modbus_local_gateway.const import DOMAIN

# pylint: disable=unexpected-keyword-arg
# pylint: disable=protected-access


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
