"""Device registry tests: the gateway device and the devices behind it.

Every other setup test patches `async_forward_entry_setups` away, so nothing
else reaches `device_registry.async_get_or_create` - which is exactly where an
argument the installed Home Assistant does not know about becomes a TypeError
for every entity on every platform. These tests set the integration up for real
against the real device and entity registries.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import (
    CONF_DEVICE_ID,
    CONF_PREFIX,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)

from .conftest import gateway_data

HOST = "127.0.0.1"
PORT = 502
DEVICE_ID = 1
FILENAME = "MOD-6000TL-X.yaml"
# The config entry is the connection, so its device carries no prefix and no
# slave id. Devices behind it are keyed by prefix, connection and slave id.
GATEWAY_IDENTIFIER = (DOMAIN, f"ModbusGateway-{HOST}:{PORT}")
CHILD_KEY = f"test-{HOST}:{PORT}:{DEVICE_ID}"


@asynccontextmanager
async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> AsyncGenerator[None]:
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
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield


def _entry(
    connection_type: str = "socket", slave_ids: tuple[int, ...] = (DEVICE_ID,)
) -> MockConfigEntry:
    """A config entry for a gateway with one device behind it per slave id."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=gateway_data(HOST, PORT, connection_type),
        version=2,
        subentries_data=[
            {
                "subentry_type": SUBENTRY_TYPE_DEVICE,
                "title": f"slave {slave_id}",
                "unique_id": f"test-{HOST}:{PORT}:{slave_id}",
                "data": {
                    CONF_PREFIX: "test",
                    CONF_DEVICE_ID: slave_id,
                    "filename": FILENAME,
                    "refresh": 30,
                    "write_function": 1,
                },
            }
            for slave_id in slave_ids
        ],
    )


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

    # The device belongs to the sub-entry, and the entities with it.
    assert child.config_subentry_id in entry.subentries
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert entities
    assert all(
        entity.config_subentry_id == child.config_subentry_id for entity in entities
    )


@pytest.mark.asyncio
async def test_gateway_device_belongs_to_the_entry_not_a_subentry(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """The gateway device is the connection's, so no sub-entry owns it."""
    entry = _entry()
    async with _setup(hass, entry):
        pass

    gateway = next(
        device
        for device in _devices(hass, entry)
        if GATEWAY_IDENTIFIER in device.identifiers
    )
    assert gateway.config_subentry_id is None
    assert gateway.config_entries == {entry.entry_id}


@pytest.mark.asyncio
async def test_reload_leaves_the_devices_alone(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """An upgrade reloads the entry without duplicating devices or re-parenting.

    Devices are matched on their identifiers and entities on their unique ids, so
    loading over an existing installation finds the entries it made last time
    rather than making new ones.
    """
    entry = _entry()
    async with _setup(hass, entry):
        before = _devices_by_identifier(hass, entry)
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert _devices_by_identifier(hass, entry) == before
    assert len(before) == 2


@pytest.mark.asyncio
async def test_every_sub_entry_gets_its_own_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Two devices behind one gateway are two devices, with one shared client."""
    entry = _entry(slave_ids=(1, 2))

    client = AsyncMock(spec=AsyncModbusTcpClientGateway)
    client.connected = True
    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "async_get_client_connection",
            return_value=client,
        ),
    ):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    identifiers = {frozenset(device.identifiers) for device in _devices(hass, entry)}
    assert identifiers == {
        frozenset({GATEWAY_IDENTIFIER}),
        frozenset({(DOMAIN, CHILD_KEY), (DOMAIN, f"{CHILD_KEY}-1")}),
        frozenset({
            (DOMAIN, f"test-{HOST}:{PORT}:2"),
            (DOMAIN, f"test-{HOST}:{PORT}:2-2"),
        }),
    }


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


@pytest.mark.asyncio
async def test_child_devices_use_via_device_id_not_the_deprecated_argument(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A child is linked with `via_device_id`, never the deprecated `via_device`.

    Home Assistant deprecated `via_device` in favour of `via_device_id`, and this
    integration is supported only on releases that know the new spelling, so the
    old one must not be passed anywhere.
    """
    entry = _entry()
    calls: list[dict[str, Any]] = []
    original = dr.DeviceRegistry.async_get_or_create

    def _record(registry: dr.DeviceRegistry, **kwargs: Any) -> dr.DeviceEntry:
        calls.append(kwargs)
        return original(registry, **kwargs)

    with patch.object(dr.DeviceRegistry, "async_get_or_create", _record):
        async with _setup(hass, entry):
            pass

    assert calls
    assert all("via_device" not in call for call in calls)
    assert any(call.get("via_device_id") for call in calls)
