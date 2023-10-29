"""Sensor tests"""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN


async def test_setup_entry(hass):
    """Test the HA setup function"""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "simple config",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
