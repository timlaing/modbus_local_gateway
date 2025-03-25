"""The Modbus Local Gateway sensor integration."""

import logging

import getmac
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
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

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Load the saved entities."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    gateway_key: str = get_gateway_key(entry=entry, with_slave=True)

    device_registry: dr.DeviceRegistry = dr.async_get(hass)

    mac: str | None = getmac.get_mac_address(hostname=entry.data[CONF_HOST])
    connections: set[tuple[str, str]] | None = (
        {(dr.CONNECTION_NETWORK_MAC, mac)} if mac else None
    )

    _LOGGER.debug("mac address for host is: %s", mac)

    device: dr.DeviceEntry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (
                DOMAIN,
                f"ModbusGateway-{get_gateway_key(entry=entry, with_slave=False)}",
            )
        },
        name=f"Modbus Gateway ({get_gateway_key(entry=entry, with_slave=False)})",
        configuration_url=f"http://{entry.data[CONF_HOST]}/",
        connections=connections,
    )

    if gateway_key not in hass.data[DOMAIN]:
        client: AsyncModbusTcpClientGateway = (
            AsyncModbusTcpClientGateway.async_get_client_connection(
                host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]
            )
        )
        if client is not None:
            hass.data[DOMAIN][gateway_key] = ModbusCoordinator(
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
