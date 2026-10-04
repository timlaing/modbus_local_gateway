"""Tests for the Modbus Local Gateway config flow."""
# pylint: disable=unexpected-keyword-arg, protected-access

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigSubentryFlow,
)
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT, Platform
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pymodbus.framer import FramerType
import pytest
from pytest_homeassistant_custom_component.common import HomeAssistant, MockConfigEntry
import voluptuous as vol

from custom_components.modbus_local_gateway.config_flow import (
    ConfigFlowHandler,
    DeviceSubentryFlowHandler,
    _async_move_device,
    _device_schema,
    _dropdown,
)
from custom_components.modbus_local_gateway.const import (
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_PREFIX,
    CONF_RESTORE_ENTITY_IDS,
    DOMAIN,
    OPTIONS_EXPECTED_OFFLINE,
    OPTIONS_REFRESH,
    OPTIONS_WRITE_FUNCTION,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.entity_management.const import WriteFunction
from custom_components.modbus_local_gateway.helpers import get_device_config
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)

from .conftest import device_data, gateway_data, mock_gateway_entry

DEVICE_INPUT = {
    CONF_DEVICE_ID: 1,
    CONF_FILENAME: "test.yaml",
    CONF_PREFIX: "test",
    OPTIONS_REFRESH: 10,
    OPTIONS_WRITE_FUNCTION: WriteFunction.SINGLE.value,
}


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
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: 502,
                CONF_CONNECTION_TYPE: "socket",
            }
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "Gateway connection"}

        mock_client.connected = True
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: 502,
                CONF_CONNECTION_TYPE: "socket",
            }
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Modbus Gateway (127.0.0.1:502)"
        assert result["data"] == gateway_data("127.0.0.1", 502)
        assert result["version"] == 2


@pytest.mark.asyncio
async def test_async_step_user_stores_the_entity_id_choice(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """The choice about entity ids is stored with the gateway.

    It has to survive a restart: an upgrade that finds it unset has to keep
    every existing entity id exactly as it was.
    """
    flow = ConfigFlowHandler()
    flow.hass = hass
    mock_client.connected = True

    with patch(
        "custom_components.modbus_local_gateway.config_flow.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=mock_client,
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: 502,
                CONF_CONNECTION_TYPE: "socket",
                CONF_LEGACY_ENTITY_IDS: True,
            }
        )

    assert result["data"][CONF_LEGACY_ENTITY_IDS] is True


@pytest.mark.asyncio
async def test_async_step_user_default_is_legacy_entity_ids(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """A gateway that says nothing keeps the entity ids it already has.

    Prefixing them is only for entities created from here on, so it has to be
    asked for.
    """
    flow = ConfigFlowHandler()
    flow.hass = hass
    mock_client.connected = True

    with patch(
        "custom_components.modbus_local_gateway.config_flow.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=mock_client,
    ):
        result = await flow.async_step_user(
            user_input={CONF_HOST: "127.0.0.1", CONF_PORT: 502}
        )

    assert result["data"][CONF_LEGACY_ENTITY_IDS] is CONF_LEGACY_ENTITY_IDS_DEFAULT
    assert CONF_LEGACY_ENTITY_IDS_DEFAULT is True


@pytest.mark.asyncio
async def test_async_step_user_offers_standard_connection_type_names(
    hass: HomeAssistant,
) -> None:
    """The framer is offered under its protocol name, not an internal one.

    The stored value is the `FramerType`, so the label has to describe the
    protocol on the wire for a user to pick the right one.
    """
    flow = ConfigFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == FlowResultType.FORM

    assert result["data_schema"] is not None
    options = next(
        validator.config["options"]
        for key, validator in result["data_schema"].schema.items()
        if str(key.schema) == CONF_CONNECTION_TYPE
    )
    assert options == [
        {"value": FramerType.SOCKET.value, "label": "Modbus TCP"},
        {"value": FramerType.RTU.value, "label": "Modbus RTU over TCP"},
    ]


@pytest.mark.asyncio
async def test_async_step_user_aborts_on_a_known_gateway(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """A second entry for the same connection is refused.

    One connection is one config entry with one socket and one gateway device.
    """
    mock_gateway_entry().add_to_hass(hass)

    flow = ConfigFlowHandler()
    flow.hass = hass
    mock_client.connected = True

    with patch(
        "custom_components.modbus_local_gateway.config_flow.AsyncModbusTcpClientGateway"
        ".async_get_client_connection",
        return_value=mock_client,
    ):
        result = await flow.async_step_user(
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 123,
                CONF_CONNECTION_TYPE: "socket",
            }
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_async_step_user_aborts_on_an_unsupported_home_assistant(
    hass: HomeAssistant,
) -> None:
    """An old Home Assistant is told so instead of being left half configured."""
    flow = ConfigFlowHandler()
    flow.hass = hass

    with patch(
        "custom_components.modbus_local_gateway.config_flow"
        ".is_supported_home_assistant",
        return_value=False,
    ):
        result = await flow.async_step_user(user_input=None)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unsupported_home_assistant_version"


@pytest.mark.asyncio
async def test_gateway_flow_asks_for_the_first_device(
    hass: HomeAssistant, mock_client: AsyncMock, enable_custom_integrations: None
) -> None:
    """A gateway is not left empty: the device flow follows it.

    The gateway says where to read, the device says what to read, so the second
    half of the configuration is asked for as soon as the first half is stored.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=mock_client,
        ),
        patch.object(mock_client, "connected", True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "localhost", CONF_PORT: 123, CONF_CONNECTION_TYPE: "socket"},
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "next_flow" in result
    assert result["next_flow"][0] == "config_subentries_flow"

    # The flow is waiting for the first device, not finished.
    assert ConfigSubentryFlow is not None
    assert result["next_flow"] != (FlowResultType.ABORT, None)


def _reachable_client() -> AsyncMock:
    """A client whose gateway answers, so a connection can be stored."""
    client = AsyncMock(spec=AsyncModbusTcpClientGateway)
    client.connected = True
    return client


@pytest.mark.asyncio
async def test_async_step_reconfigure_refuses_an_unreachable_gateway(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A gateway that does not answer is not stored as the connection.

    Every device behind the entry reads through that connection, so saving a
    host and port nothing answers on would make all of them unavailable, and the
    form is the only place to say so.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    unreachable = AsyncMock(spec=AsyncModbusTcpClientGateway)
    unreachable.connected = False

    result = await entry.start_reconfigure_flow(hass)
    with patch(
        "custom_components.modbus_local_gateway.config_flow"
        ".AsyncModbusTcpClientGateway.async_get_client_connection",
        return_value=unreachable,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "10.0.0.5",
                CONF_PORT: 502,
                CONF_CONNECTION_TYPE: "socket",
                CONF_LEGACY_ENTITY_IDS: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "Gateway connection"}
    assert entry.data == gateway_data()


@pytest.mark.asyncio
async def test_async_step_reconfigure(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Changing the connection of a gateway keeps its devices and entities.

    The devices behind it are sub-entries, so they are not touched: their entity
    ids, unique ids, device ids and history stay where they are.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.modbus_local_gateway.config_flow"
        ".AsyncModbusTcpClientGateway.async_get_client_connection",
        return_value=_reachable_client(),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "10.0.0.5",
                CONF_PORT: 502,
                CONF_CONNECTION_TYPE: "socket",
                CONF_LEGACY_ENTITY_IDS: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == gateway_data("10.0.0.5", 502)
    assert entry.title == "Modbus Gateway (10.0.0.5:502)"
    assert len(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)) == 1


@pytest.mark.asyncio
async def test_async_step_reconfigure_offers_the_restore(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """A gateway in the pre-2026.02 style is offered the entity ids back."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    fields = {str(key.schema) for key in result["data_schema"].schema}
    assert CONF_RESTORE_ENTITY_IDS in fields


@pytest.mark.asyncio
async def test_async_step_reconfigure_has_no_restore_to_offer_when_new(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """There is nothing to restore for entities created in the host style."""
    entry = mock_gateway_entry(legacy_entity_ids=False)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    fields = {str(key.schema) for key in result["data_schema"].schema}
    assert CONF_RESTORE_ENTITY_IDS not in fields


@pytest.mark.asyncio
async def test_async_step_reconfigure_restores_entity_ids(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Restoring is done when asked for, and only then.

    Nothing else may rename an entity: a forced rename breaks the automations and
    history that use the old one.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    with (
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=_reachable_client(),
        ),
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".async_restore_legacy_entity_ids",
            AsyncMock(),
        ) as restore,
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 123,
                CONF_CONNECTION_TYPE: "socket",
                CONF_LEGACY_ENTITY_IDS: True,
                CONF_RESTORE_ENTITY_IDS: True,
            },
        )
        await hass.async_block_till_done()

    restore.assert_awaited_once_with(hass, entry)


@pytest.mark.asyncio
async def test_async_step_reconfigure_without_restore_leaves_entity_ids(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Reconfiguring without asking for a restore changes no entity id."""
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    with (
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=_reachable_client(),
        ),
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".async_restore_legacy_entity_ids",
            AsyncMock(),
        ) as restore,
    ):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: 123,
                CONF_CONNECTION_TYPE: "socket",
                CONF_LEGACY_ENTITY_IDS: True,
                CONF_RESTORE_ENTITY_IDS: False,
            },
        )
        await hass.async_block_till_done()

    restore.assert_not_awaited()


@pytest.mark.asyncio
async def test_async_step_reconfigure_refuses_a_known_gateway(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Two config entries cannot point at one connection."""
    mock_gateway_entry().add_to_hass(hass)
    other = mock_gateway_entry()
    other.add_to_hass(hass)

    result = await other.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "localhost",
            CONF_PORT: 123,
            CONF_CONNECTION_TYPE: "socket",
            CONF_LEGACY_ENTITY_IDS: True,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "already_configured"}


@pytest.mark.asyncio
async def test_async_get_subentry_flow() -> None:
    """The gateway flow declares the device flow of its sub-entries."""
    assert ConfigFlowHandler.async_get_supported_subentry_types(
        MockConfigEntry(domain=DOMAIN)
    ) == {SUBENTRY_TYPE_DEVICE: DeviceSubentryFlowHandler}


@pytest.mark.asyncio
async def test_async_step_user_creates_a_subentry(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A device behind the gateway becomes a sub-entry of it."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test slave 1"
    subentries = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)
    assert len(subentries) == 1
    subentry = subentries[0]
    assert subentry.unique_id == "test-localhost:123:1"
    assert dict(subentry.data) == device_data(1, prefix="test", refresh=10)


@pytest.mark.asyncio
async def test_async_step_user_stores_whether_a_device_is_expected_offline(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A device that switches itself off says so, and the setting is kept.

    It is what tells a solar inverter going quiet at dusk apart from a device
    that has fallen off the bus, so it has to survive being stored rather than
    being asked for again on every poll.
    """
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT | {OPTIONS_EXPECTED_OFFLINE: True}
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    subentry = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[0]
    assert dict(subentry.data) == device_data(
        1, prefix="test", refresh=10, expected_offline=True
    )


@pytest.mark.asyncio
async def test_async_step_user_refuses_a_known_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """One device is added once: two entries cannot read the same slave id."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_DEVICE_ID: "device_id_taken"}
    assert len(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)) == 1


@pytest.mark.asyncio
async def test_async_step_user_keeps_the_same_prefix_apart(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """The prefix is part of the key, so it can tell two devices apart.

    Two devices behind one gateway can have the same slave id and the same YAML
    file; the prefix is what keeps their entity ids apart.
    """
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], {**DEVICE_INPUT, CONF_PREFIX: "shed"}
        )

    assert {
        sub.unique_id for sub in entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)
    } == {"test-localhost:123:1", "shed-localhost:123:1"}


@pytest.mark.asyncio
async def test_async_step_user_refuses_an_unknown_file(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A file that cannot be read is refused before anything is stored."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(side_effect=FileNotFoundError),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_FILENAME: "file_not_found"}
    assert not entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)


@pytest.mark.asyncio
async def test_async_step_reconfigure_updates_the_subentry(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Changing a device's settings keeps its device where the user put it.

    The prefix and the slave id are in the registry identifiers, so they are
    renamed in place: the device keeps its id, and with it its area, its history
    and the dashboard cards pointing at it.
    """
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "test-localhost:123:1")},
        name="test slave 1",
    )
    device_id = device.id

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

        subentry_id = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[0].subentry_id
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={
                "source": SOURCE_RECONFIGURE,
                "subentry_id": subentry_id,
            },
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"],
            {
                **DEVICE_INPUT,
                CONF_DEVICE_ID: 2,
                CONF_PREFIX: "shed",
                OPTIONS_REFRESH: 30,
                OPTIONS_WRITE_FUNCTION: WriteFunction.MULTIPLE.value,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    subentry = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[0]
    assert subentry.unique_id == "shed-localhost:123:2"
    assert dict(subentry.data) == device_data(
        2,
        prefix="shed",
        refresh=30,
        write_function=WriteFunction.MULTIPLE.value,
    )

    moved = registry.async_get(device_id)
    assert moved is not None
    assert moved.identifiers == {
        (DOMAIN, "shed-localhost:123:2"),
        (DOMAIN, "shed-localhost:123:2-2"),
    }


@pytest.mark.asyncio
async def test_moving_a_device_renames_the_unique_ids_of_its_entities(
    hass: HomeAssistant,
) -> None:
    """The entities of a moved device follow it.

    Their unique ids carry the prefix and the slave id of the device, so leaving
    them behind would make Home Assistant create a second set of entities and
    leave the first one - with the history in it - behind as dead entries.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    subentry = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[0]

    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, "test-localhost:123:1"),
            (DOMAIN, "test-localhost:123:1-1"),
        },
        name="test slave 1",
    )
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        "test-1-firmware_version",
        config_entry=entry,
        device_id=device.id,
        config_subentry_id=subentry.subentry_id,
    )
    entity_id = entity.entity_id

    _async_move_device(
        hass=hass,
        entry=entry,
        subentry=subentry,
        config={
            **get_device_config(entry, subentry),
            CONF_PREFIX: "shed",
            CONF_DEVICE_ID: 2,
        },
    )

    moved = entity_registry.async_get(entity_id)
    assert moved is not None
    assert moved.unique_id == "shed-2-firmware_version"
    assert moved.device_id == device.id


@pytest.mark.asyncio
async def test_async_step_reconfigure_keeps_the_device_where_it_is(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """A reconfigure that changes nothing but the refresh rate moves nothing."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, "test-localhost:123:1"),
            (DOMAIN, "test-localhost:123:1-1"),
        },
        name="test slave 1",
    )

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={
                "source": SOURCE_RECONFIGURE,
                "subentry_id": entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[
                    0
                ].subentry_id,
            },
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], {**DEVICE_INPUT, OPTIONS_REFRESH: 45}
        )
        await hass.async_block_till_done()

    unchanged = registry.async_get(device.id)
    assert unchanged is not None
    assert unchanged.identifiers == {
        (DOMAIN, "test-localhost:123:1"),
        (DOMAIN, "test-localhost:123:1-1"),
    }


@pytest.mark.asyncio
async def test_async_step_reconfigure_refuses_the_slave_id_of_another_device(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """A reconfigure cannot move one device onto another."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    with patch(
        "custom_components.modbus_local_gateway.config_flow.create_device_info",
        MagicMock(),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], DEVICE_INPUT
        )

        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={"source": SOURCE_USER},
        )
        await hass.config_entries.subentries.async_configure(
            result["flow_id"], {**DEVICE_INPUT, CONF_DEVICE_ID: 2}
        )

        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_TYPE_DEVICE),
            context={
                "source": SOURCE_RECONFIGURE,
                "subentry_id": entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[
                    0
                ].subentry_id,
            },
        )
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {**DEVICE_INPUT, CONF_DEVICE_ID: 2}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_DEVICE_ID: "device_id_taken"}


def test_write_function_must_be_known() -> None:
    """An unknown write function is refused by the form."""
    schema = _device_schema({"test.yaml": "Test Test"})
    with pytest.raises(vol.Invalid):
        schema({**DEVICE_INPUT, OPTIONS_WRITE_FUNCTION: "nonsense"})


def test_write_function_defaults_to_single() -> None:
    """An entry that never chose a write function keeps the one it had."""
    schema = _device_schema({"test.yaml": "Test Test"})
    defaults = {
        str(key.schema): key.default()
        for key in schema.schema
        if key.default is not vol.UNDEFINED
    }
    assert defaults[OPTIONS_WRITE_FUNCTION] == WriteFunction.SINGLE.value


def test_drop_in_labels_the_framer_types() -> None:
    """The dropdown offers protocol names."""
    selector = _dropdown({
        FramerType.SOCKET.value: "Modbus TCP",
        FramerType.RTU.value: "Modbus RTU over TCP",
    })
    assert selector.config["options"] == [
        {"value": FramerType.SOCKET.value, "label": "Modbus TCP"},
        {"value": FramerType.RTU.value, "label": "Modbus RTU over TCP"},
    ]
