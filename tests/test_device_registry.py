"""Device registry tests: the gateway device and the devices behind it.

Every other setup test patches `async_forward_entry_setups` away, so nothing
else reaches `device_registry.async_get_or_create` - which is exactly where an
argument the installed Home Assistant does not know about becomes a TypeError
for every entity on every platform. These tests set the integration up for real
against the real device and entity registries.

The link back to the gateway is written with whichever of `via_device_id` and
`via_device` the installed HA accepts, so which argument these run through
depends on the version under test: the legacy one here, the current one on the
HA dev workflow. The unit tests at the end cover both branches on either.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import getmac
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_PREFIX,
    DOMAIN,
)
from custom_components.modbus_local_gateway.helpers import via_device
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)

HOST = "127.0.0.1"
PORT = 502
DEVICE_ID = 1
# The coordinator keys on host, port and device id; the gateway device is
# registered once per host and port.
GATEWAY_KEY = f"test-{HOST}:{PORT}"
GATEWAY_IDENTIFIER = (DOMAIN, f"ModbusGateway-{GATEWAY_KEY}")
CHILD_KEY = f"{GATEWAY_KEY}:{DEVICE_ID}"
GATEWAY_DEVICE_ID = "0123456789abcdef0123456789abcdef"


def _gateway_device() -> dr.DeviceEntry:
    """A parent device as the registry hands it out.

    Only the two fields `via_device` reads are given, rather than constructing a
    `DeviceEntry`: that is an attrs class whose keyword arguments differ between
    the two Home Assistant generations, and this test has to build one on
    either.
    """
    return cast(
        dr.DeviceEntry,
        SimpleNamespace(id=GATEWAY_DEVICE_ID, identifiers={GATEWAY_IDENTIFIER}),
    )


@asynccontextmanager
async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> AsyncIterator[None]:
    """Set the config entry up the way Home Assistant does, not by hand."""
    client = AsyncMock(spec=AsyncModbusTcpClientGateway)
    client.connected = True
    for method in (
        "async_get_holding_registers",
        "async_get_input_registers",
        "async_get_coils",
        "async_get_discrete_input",
    ):
        setattr(client, method, AsyncMock(return_value=[]))

    entry.add_to_hass(hass)
    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "async_get_client_connection",
            return_value=client,
        ),
        patch.object(getmac, "get_mac_address", return_value="aa:bb:cc:dd:ee:ff"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield


def _entry(connection_type: str | None = None) -> MockConfigEntry:
    """A config entry pointing at a device config we ship."""
    data: dict[str, object] = {
        "host": HOST,
        "port": PORT,
        CONF_DEVICE_ID: DEVICE_ID,
        CONF_PREFIX: "test",
        "filename": "MOD-6000TL-X.yaml",
    }
    if connection_type is not None:
        data[CONF_CONNECTION_TYPE] = connection_type
    return MockConfigEntry(domain=DOMAIN, data=data, version=1)


def _devices(hass: HomeAssistant, entry: MockConfigEntry) -> list[dr.DeviceEntry]:
    return list(dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id))


def _devices_by_identifier(
    hass: HomeAssistant, entry: MockConfigEntry
) -> dict[frozenset[tuple[str, str]], str]:
    """The entry's devices as identifiers to id, the way a registry lookup sees them."""
    return {
        frozenset(device.identifiers): device.id for device in _devices(hass, entry)
    }


@pytest.mark.asyncio
async def test_entities_hang_off_the_gateway_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A child's parent is the gateway device, and its entities are registered."""
    entry = _entry()
    async with _setup(hass, entry):
        pass

    devices = _devices(hass, entry)
    assert len(devices) == 2

    gateway = next(
        device for device in devices if GATEWAY_IDENTIFIER in device.identifiers
    )
    child = next(device for device in devices if device is not gateway)

    assert child.via_device_id == gateway.id
    assert child.identifiers == {
        (DOMAIN, CHILD_KEY),
        (DOMAIN, f"{CHILD_KEY}-{DEVICE_ID}"),
    }

    # Adding the entity is what registers the device, so this is where an
    # argument the installed HA does not know fails every entity at once.
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


@pytest.mark.asyncio
async def test_reload_leaves_the_devices_alone(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """An upgrade reloads the entry without duplicating devices or re-parenting.

    Both arguments end up in the same stored `via_device_id`, and devices are
    matched on their identifiers, so loading over an existing installation finds
    the entries it made last time rather than making new ones.
    """
    entry = _entry()
    async with _setup(hass, entry):
        before = _devices_by_identifier(hass, entry)
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert _devices_by_identifier(hass, entry) == before
    assert len(before) == 2


@pytest.mark.asyncio
async def test_no_gateway_device_means_no_parent(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """An entry that brings no gateway device still works, and stands alone."""
    entry = _entry(connection_type="rtu")
    async with _setup(hass, entry):
        pass

    devices = _devices(hass, entry)
    assert len(devices) == 1
    assert devices[0].via_device_id is None
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


def test_via_device_id_is_used_when_the_registry_takes_it() -> None:
    """On the current HA the child is given the parent's device id."""
    with patch(
        "custom_components.modbus_local_gateway.helpers._VIA_DEVICE_ID_SUPPORTED", True
    ):
        assert via_device(_gateway_device()) == {"via_device_id": GATEWAY_DEVICE_ID}


def test_via_device_identifiers_are_used_when_it_does_not() -> None:
    """On the older HA the child is given the parent's identifier instead."""
    with patch(
        "custom_components.modbus_local_gateway.helpers._VIA_DEVICE_ID_SUPPORTED", False
    ):
        assert via_device(_gateway_device()) == {"via_device": GATEWAY_IDENTIFIER}
