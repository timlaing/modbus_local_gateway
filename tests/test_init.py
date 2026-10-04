"""Setup, unload, migration and version guard tests"""
# pylint: disable=unexpected-keyword-arg, protected-access

from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryDisabler, ConfigSubentry
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    HomeAssistant,
    MockConfigEntry,
)

from custom_components.modbus_local_gateway import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.modbus_local_gateway.const import (
    CONF_DEVICE_ID,
    CONF_LEGACY_ENTITY_IDS,
    CONF_PREFIX,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)

from .conftest import (
    device_data,
    device_subentry,
    gateway_data,
    mock_gateway_entry,
    mock_runtime,
)


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""
    mock_config_entry = mock_gateway_entry()
    mock_config_entry.add_to_hass(hass)
    # The devices are read once setup is over, so the connection a setup asks for
    # is not one a test should let out onto the network.
    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(spec=AsyncModbusTcpClientGateway),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
        patch.object(ModbusCoordinator, "async_schedule_initial_poll"),
    ):
        await async_setup_entry(hass, mock_config_entry)

    rtu_entry = mock_gateway_entry(connection_type="rtu")
    rtu_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(spec=AsyncModbusTcpClientGateway),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
        patch.object(ModbusCoordinator, "async_schedule_initial_poll"),
    ):
        await async_setup_entry(hass, rtu_entry)


@pytest.mark.asyncio
async def test_setup_entry_without_client_is_not_ready(hass: HomeAssistant) -> None:
    """An unreachable gateway must not be set up."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_setup_entry_one_coordinator_per_subentry(hass: HomeAssistant) -> None:
    """Every device behind a gateway gets its own coordinator."""
    entry = mock_gateway_entry(slave_ids=[1, 2])
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
    ):
        await async_setup_entry(hass, entry)

    coordinators = entry.runtime_data.coordinators
    assert len(coordinators) == 2
    assert {coordinator.gateway for coordinator in coordinators.values()} == {
        "test-localhost:123:1",
        "test-localhost:123:2",
    }
    # One client per connection, shared by its devices.
    assert {id(coordinator.client) for coordinator in coordinators.values()} == {
        id(next(iter(coordinators.values())).client)
    }


@pytest.mark.asyncio
async def test_setup_entry_skips_a_device_whose_file_is_gone(
    hass: HomeAssistant,
) -> None:
    """A missing device file takes down that device only.

    Device files live in a folder the user maintains, so one of them can be
    renamed or deleted at any time. The devices behind the same gateway do not
    depend on it.
    """
    data = gateway_data()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        subentries_data=[
            device_subentry(
                device_data(1), unique_id=f"test-{data['host']}:{data['port']}:1"
            ),
            device_subentry(
                device_data(2, filename="gone.yaml"),
                unique_id=f"test-{data['host']}:{data['port']}:2",
            ),
        ],
    )
    entry.add_to_hass(hass)
    subentries = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)

    def create_device_info(
        _hass: HomeAssistant, filename: str, *_args: object, **_kwargs: object
    ) -> MagicMock:
        if filename == "gone.yaml":
            raise FileNotFoundError(filename)
        return MagicMock(model="Model", manufacturer="Manufacturer")

    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.modbus_local_gateway.create_device_info",
            side_effect=create_device_info,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
        patch("custom_components.modbus_local_gateway._LOGGER.error") as error,
    ):
        await async_setup_entry(hass, entry)

    assert list(entry.runtime_data.coordinators) == [subentries[0].subentry_id]
    assert "gone.yaml" in str(error.call_args)


@pytest.mark.asyncio
async def test_setup_entry_reads_the_devices_after_setup(hass: HomeAssistant) -> None:
    """Setup schedules the first read of every device; it does not wait for it.

    Home Assistant waits for the work that setup starts, and a read of a device
    that is not answering takes a timeout sequence per attempt - so the devices
    are read once each, after the platforms are up and after startup is over.
    """
    entry = mock_gateway_entry(slave_ids=[1, 2])
    entry.add_to_hass(hass)
    client = MagicMock(spec=AsyncModbusTcpClientGateway)

    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=client,
        ),
        patch(
            "custom_components.modbus_local_gateway.create_device_info",
            return_value=MagicMock(model="Model", manufacturer="Manufacturer"),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
        patch.object(ModbusCoordinator, "async_schedule_initial_poll") as schedule,
    ):
        await async_setup_entry(hass, entry)

        # Once per device behind the gateway, and nothing was read while doing it.
        assert schedule.call_count == 2
        client.update_device.assert_not_called()


@pytest.mark.asyncio
async def test_unload_entry_drops_the_pending_first_read(
    hass: HomeAssistant,
) -> None:
    """Unloading must not leave a first read waiting to touch a closed client."""
    entry = mock_gateway_entry()
    client = MagicMock(spec=AsyncModbusTcpClientGateway)
    coordinator = _coordinator(client)
    entry.runtime_data = mock_runtime({"sub": coordinator}, client)

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ),
        patch.object(hass.config_entries, "async_loaded_entries", return_value=[entry]),
    ):
        assert await async_unload_entry(hass, entry) is True

    coordinator.async_cancel_initial_poll.assert_called_once()


def _coordinator(client: MagicMock) -> MagicMock:
    """A coordinator as the runtime holds it: one per device, sharing a client."""
    return MagicMock(spec=ModbusCoordinator, client=client)


@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant) -> None:
    """Unloading the last entry on a gateway must close its client.

    Leaving it open keeps the socket - and pymodbus' retries - alive after the
    entry is gone, so a disabled entry carries on talking to the device.
    """
    entry = mock_gateway_entry()
    client = MagicMock(spec=AsyncModbusTcpClientGateway)
    entry.runtime_data = mock_runtime({"sub": _coordinator(client)}, client)

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ) as unload_patch,
        patch.object(hass.config_entries, "async_loaded_entries", return_value=[entry]),
    ):
        result: bool = await async_unload_entry(hass, entry)
        assert result is True
        unload_patch.assert_awaited_once()
        assert not entry.runtime_data.coordinators
        client.close_cached.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_without_devices(hass: HomeAssistant) -> None:
    """A gateway with no devices behind it must still close its client.

    Between creating a gateway and adding its first device there are no
    coordinators at all, so the client has to be remembered from setup rather
    than read back out of them.
    """
    entry = mock_gateway_entry(slave_ids=[])
    client = MagicMock(spec=AsyncModbusTcpClientGateway)
    entry.runtime_data = mock_runtime({}, client)

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ),
        patch.object(hass.config_entries, "async_loaded_entries", return_value=[entry]),
    ):
        assert await async_unload_entry(hass, entry) is True
        client.close_cached.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_closes_the_client_of_setup(
    hass: HomeAssistant,
) -> None:
    """Unloading after a reconfigure must close the connection setup opened.

    Reconfiguring changes the host and port of the entry, so the settings of the
    entry no longer name the connection the entry is holding open.
    """
    entry = mock_gateway_entry(host="127.0.0.1", port=1234)
    entry.add_to_hass(hass)
    client: AsyncModbusTcpClientGateway = (
        AsyncModbusTcpClientGateway.async_get_client_connection(
            host="127.0.0.1", port=1234, connection_type="socket"
        )
    )

    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=client,
        ),
        patch(
            "custom_components.modbus_local_gateway.create_device_info",
            return_value=MagicMock(model="Model", manufacturer="Manufacturer"),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            AsyncMock(return_value=True),
        ),
    ):
        assert await async_setup_entry(hass, entry) is True

    assert client in AsyncModbusTcpClientGateway._CLIENT.values()

    # What async_update_entry does before the reload a reconfigure schedules.
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "host": "192.168.1.50", "port": 502}
    )

    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
        ),
        patch.object(hass.config_entries, "async_loaded_entries", return_value=[entry]),
        patch.object(client, "close") as close_patch,
    ):
        assert await async_unload_entry(hass, entry) is True
        close_patch.assert_called_once()

    assert client not in AsyncModbusTcpClientGateway._CLIENT.values()
    AsyncModbusTcpClientGateway._CLIENT.pop("127.0.0.1:1234:socket", None)


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_shared_client(hass: HomeAssistant) -> None:
    """A client shared with another entry on the same gateway must stay open.

    One client is cached per host/port/framer, so two gateways on the same
    connection share it. Closing it on the first unload would kill the second.
    """
    shared_client = MagicMock()
    entry = mock_gateway_entry()
    other = mock_gateway_entry()
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    entry.runtime_data = mock_runtime(
        {"sub": _coordinator(shared_client)}, shared_client
    )
    other.runtime_data = mock_runtime(
        {"sub": _coordinator(shared_client)}, shared_client
    )

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=True),
        ),
        patch.object(
            hass.config_entries, "async_loaded_entries", return_value=[entry, other]
        ),
    ):
        assert await async_unload_entry(hass, entry) is True
        shared_client.close_cached.assert_not_called()


@pytest.mark.asyncio
async def test_async_unload_entry_keeps_state_when_platforms_fail(
    hass: HomeAssistant,
) -> None:
    """A failed platform unload must leave the entry intact.

    Entities are still loaded at that point, so closing the shared client would
    strand them on a dead connection - and returning True would tell Home
    Assistant the entry had gone.
    """
    entry = mock_gateway_entry()
    coordinator = _coordinator(MagicMock())
    client = MagicMock(spec=AsyncModbusTcpClientGateway)
    entry.runtime_data = mock_runtime({"sub": coordinator}, client)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        AsyncMock(return_value=False),
    ):
        assert await async_unload_entry(hass, entry) is False
        assert entry.runtime_data.coordinators == {"sub": coordinator}
        client.close_cached.assert_not_called()


def _v1_entry(
    entry_id: str,
    slave_id: int = 1,
    prefix: str = "test",
    host: str = "localhost",
    port: int = 123,
    filename: str = "test.yaml",
    disabled_by: ConfigEntryDisabler | None = None,
) -> MockConfigEntry:
    """A config entry as version 1 wrote it: one entry per device."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        data={
            "host": host,
            "port": port,
            CONF_DEVICE_ID: slave_id,
            CONF_PREFIX: prefix,
            "filename": filename,
            "name": "simple config",
        },
        options={"refresh": 45, "write_function": 2},
        version=1,
        disabled_by=disabled_by,
        title=f"{prefix} device {slave_id}",
    )


@pytest.mark.asyncio
async def test_migration_moves_devices_and_entities_into_subentries(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """One device behind a gateway becomes one sub-entry of one entry.

    Everything that identifies an entity, a device or a config entry stays: the
    entity ids, unique ids and device ids are what automations, dashboards and
    history are written against.
    """
    entry = _v1_entry("a" * 26, filename="MOD-6000TL-X.yaml")
    entry.add_to_hass(hass)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test-localhost:123:1")},
        name="test Growatt",
    )
    device_id = device.id
    entity = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "test-1-firmware_version",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id="test_firmware_version",
    )
    entity_id = entity.entity_id

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    migrated = entries[0]
    assert migrated.entry_id == entry.entry_id
    assert migrated.version == 2
    assert migrated.data == gateway_data("localhost", 123)
    assert migrated.data[CONF_LEGACY_ENTITY_IDS] is True
    assert migrated.options == {}

    subentries = migrated.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)
    assert len(subentries) == 1
    subentry = subentries[0]
    assert subentry.unique_id == "test-localhost:123:1"
    assert dict(subentry.data) == device_data(
        1, filename="MOD-6000TL-X.yaml", refresh=45, write_function=2
    )

    moved_device = device_registry.async_get(device_id)
    assert moved_device is not None
    assert moved_device.config_subentry_id == subentry.subentry_id
    # Version 1 wrote one identifier; setup adds the slave id one on first load.
    assert moved_device.identifiers == {(DOMAIN, "test-localhost:123:1")}

    moved_entity = entity_registry.async_get(entity_id)
    assert moved_entity is not None
    assert moved_entity.config_subentry_id == subentry.subentry_id
    assert moved_entity.unique_id == "test-1-firmware_version"
    assert moved_entity.device_id == device_id


@pytest.mark.asyncio
async def test_migration_merges_entries_of_one_gateway(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Two devices on one gateway become two sub-entries of one entry.

    The prefix is a per-device setting, so entries that only differ by it have
    always been the same gateway - and had the same socket open twice.
    """
    first = _v1_entry("a" * 26, slave_id=1, prefix="test", filename="MOD-6000TL-X.yaml")
    second = _v1_entry("b" * 26, slave_id=2, prefix="", filename="MOD-6000TL-X.yaml")
    first.add_to_hass(hass)
    second.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    parent = entries[0]
    assert parent.entry_id == first.entry_id
    assert parent.version == 2
    assert {
        sub.unique_id for sub in parent.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)
    } == {
        "test-localhost:123:1",
        "localhost:123:2",
    }


@pytest.mark.asyncio
async def test_migration_keeps_a_disabled_gateway_disabled(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A group of disabled entries stays disabled after being merged."""
    first = _v1_entry("a" * 26, disabled_by=ConfigEntryDisabler.USER)
    second = _v1_entry("b" * 26, slave_id=2, disabled_by=ConfigEntryDisabler.USER)
    first.add_to_hass(hass)
    second.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].disabled_by is ConfigEntryDisabler.USER


@pytest.mark.asyncio
async def test_migration_renames_the_gateway_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """The gateway device loses the prefix of the device it was created for.

    Version 1 put it in the identifier, so one connection could have one gateway
    device per device behind it. The registry renames identifiers in place, so
    the device keeps its id, its area and its place in dashboards.
    """
    entry = _v1_entry("a" * 26, filename="MOD-6000TL-X.yaml")
    entry.add_to_hass(hass)

    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ModbusGateway-test-localhost:123")},
        name="Modbus Gateway (test-localhost:123)",
    )
    device_id = device.id

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    renamed = registry.async_get(device_id)
    assert renamed is not None
    assert renamed.identifiers == {(DOMAIN, "ModbusGateway-localhost:123")}
    assert renamed.config_subentry_id is None


@pytest.mark.asyncio
async def test_migration_is_not_run_twice(hass: HomeAssistant) -> None:
    """A second start finds nothing to migrate."""
    entry = _v1_entry("a" * 26)
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True
        subentries = dict(entry.subentries)
        assert await async_setup(hass, {}) is True

    assert entry.subentries == subentries
    assert entry.version == 2


@pytest.mark.asyncio
async def test_subentries_are_stored_read_only(hass: HomeAssistant) -> None:
    """Sub-entry data is a read-only mapping, as Home Assistant requires."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    subentry = next(iter(entry.subentries.values()))
    assert isinstance(subentry.data, MappingProxyType)


@pytest.mark.asyncio
async def test_unsupported_home_assistant_is_refused(
    hass: HomeAssistant,
) -> None:
    """An old Home Assistant gets one clear error instead of a broken entry."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.modbus_local_gateway.is_supported_home_assistant",
            return_value=False,
        ),
        pytest.raises(ConfigEntryError) as err,
    ):
        await async_setup_entry(hass, entry)

    assert err.value.translation_key == "unsupported_home_assistant_version"


@pytest.mark.asyncio
async def test_new_subentry_picks_up_a_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Adding a device to a loaded gateway creates its device on reload."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    client = MagicMock(connected=True)
    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=client,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(entry.runtime_data.coordinators) == 1

        hass.config_entries.async_add_subentry(
            entry,
            ConfigSubentry(
                data=MappingProxyType(device_data(2)),
                subentry_type=SUBENTRY_TYPE_DEVICE,
                title="slave 2",
                unique_id="test-localhost:123:2",
            ),
        )
        await hass.async_block_till_done()

    assert len(entry.runtime_data.coordinators) == 2


@pytest.mark.asyncio
async def test_migration_merges_the_gateway_devices_of_one_connection(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """One connection ends up with one gateway device, on the entry kept.

    Version 1 named the gateway device after the device it was configured for,
    so two devices on one gateway had two gateway devices. The duplicate belongs
    to the entry that is about to go, so it has to move first: an entry that owns
    anything is kept rather than removed.
    """
    first = _v1_entry("a" * 26, slave_id=1, filename="MOD-6000TL-X.yaml")
    second = _v1_entry("b" * 26, slave_id=2, filename="MOD-6000TL-X.yaml")
    first.add_to_hass(hass)
    second.add_to_hass(hass)

    registry = dr.async_get(hass)
    for entry, slave_id in ((first, 1), (second, 2)):
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "ModbusGateway-test-localhost:123")},
            name=f"Modbus Gateway (test slave {slave_id})",
        )
    # The two devices have to be separate: an identifier is unique per entry.
    # Version 1 named the gateway device after the gateway and the prefix of the
    # entry it was configured for, so two prefixes on one gateway gave two
    # gateway devices with the same host and port.
    second_gateway = registry.async_get_or_create(
        config_entry_id=second.entry_id,
        identifiers={(DOMAIN, "ModbusGateway-test-localhost:123")},
        name="Modbus Gateway (test slave 2)",
    )
    second_gateway_id = second_gateway.id

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    gateway_devices = [
        device
        for device in dr.async_entries_for_config_entry(registry, entries[0].entry_id)
        if (DOMAIN, "ModbusGateway-localhost:123") in device.identifiers
    ]
    assert len(gateway_devices) == 1
    assert registry.async_get(second_gateway_id) is None


@pytest.mark.asyncio
async def test_migration_moves_a_child_onto_the_kept_gateway_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A child of a duplicate gateway follows it onto the device that is kept.

    Home Assistant clears `via_device_id` of every device whose parent is
    removed. A child whose device file is gone is not registered again by setup,
    so the parent link has to be moved before the duplicate gateway is removed.
    """
    first = _v1_entry("a" * 26, slave_id=1, prefix="test", filename="MOD-6000TL-X.yaml")
    second = _v1_entry("b" * 26, slave_id=2, prefix="shed", filename="missing.yaml")
    first.add_to_hass(hass)
    second.add_to_hass(hass)

    registry = dr.async_get(hass)
    keeper_gateway = registry.async_get_or_create(
        config_entry_id=first.entry_id,
        identifiers={(DOMAIN, "ModbusGateway-test-localhost:123")},
        name="Modbus Gateway (test)",
    )
    duplicate_gateway = registry.async_get_or_create(
        config_entry_id=second.entry_id,
        identifiers={(DOMAIN, "ModbusGateway-shed-localhost:123")},
        name="Modbus Gateway (shed)",
    )
    child = registry.async_get_or_create(
        config_entry_id=second.entry_id,
        identifiers={(DOMAIN, "shed-localhost:123:2")},
        name="Shed device",
        via_device_id=duplicate_gateway.id,
    )
    child_id = child.id

    with patch(
        "custom_components.modbus_local_gateway.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=MagicMock(connected=True),
    ):
        assert await async_setup(hass, {}) is True

    moved_child = registry.async_get(child_id)
    assert isinstance(moved_child, dr.DeviceEntry)
    assert moved_child.via_device_id == keeper_gateway.id
