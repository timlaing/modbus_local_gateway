"""The Modbus local gateway sensor integration."""

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_SLAVE_ID,
    DOMAIN,
    OPTIONS_DEFAULT_REFRESH,
    OPTIONS_REFRESH,
    PLATFORMS,
)
from .coordinator import ModbusCoordinator
from .helpers import get_gateway_key
from .tcp_client import AsyncModbusTcpClientGateway


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Load the saved entities."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    gateway_key = get_gateway_key(entry=entry, with_slave=False)

    device_registry = dr.async_get(hass)

    device: dr.DeviceEntry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"ModbusGateway-{gateway_key}")},
        name="Modbus Gateway",
        configuration_url=f"http://{entry.data[CONF_HOST]}/",
    )

    if gateway_key not in hass.data[DOMAIN]:
        client: AsyncModbusTcpClientGateway = (
            await AsyncModbusTcpClientGateway.async_get_client_connection(
                hass=hass, data=entry.data
            )
        )
        if client is not None:
            hass.data[DOMAIN][get_gateway_key(entry=entry)] = ModbusCoordinator(
                hass=hass,
                gateway_device=device,
                client=client,
                gateway=gateway_key,
                update_interval=entry.options.get(
                    OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH
                ),
            )
        else:
            raise ConfigEntryNotReady(
                f"Unable to connect to {gateway_key}, slave: {entry.data[CONF_SLAVE_ID]}"
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
