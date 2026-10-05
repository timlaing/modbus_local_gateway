"""Tests for entity ids: #168 and the explicit restore.

Nothing in this integration may rename an entity on its own. v2026.02.0 forced
every existing entity to `<ipnodots>_<yaml_key>`, which broke the automations and
the history written against the old id, and left no way to rename an entity in
the UI either.
"""

# pylint: disable=unexpected-keyword-arg, protected-access

from dataclasses import replace
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import SOURCE_USER, SubentryFlowContext
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import (
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_RESTORE_ENTITY_IDS,
    DOMAIN,
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import (
    ModbusCoordinator,
    ModbusCoordinatorEntity,
    async_restore_legacy_entity_ids,
    get_legacy_entity_id,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)

from .conftest import gateway_data, mock_gateway_entry

DESCRIPTION = ModbusEntityDescription(
    key="firmware_version",
    register_address=1,
    data_type=ModbusDataType.HOLDING_REGISTER,
)


def _description(
    key: str, control_type: Platform = Platform.SENSOR
) -> ModbusEntityDescription:
    """Return a description of an entity named by a yaml key."""
    return replace(DESCRIPTION, key=key, control_type=control_type)


def _entity(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    entity_id: str,
    unique_id: str = "test-1-firmware_version",
    device_id: str | None = None,
) -> er.RegistryEntry:
    """Register one entity of a device behind the gateway."""
    return er.async_get(hass).async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        unique_id,
        config_entry=entry,
        suggested_object_id=entity_id.split(".")[1],
        config_subentry_id=entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[
            0
        ].subentry_id,
        device_id=device_id,
    )


def _coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> ModbusCoordinator:
    """Return a coordinator as the runtime holds it for the first device."""
    subentry = entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[0]
    return ModbusCoordinator(
        hass=hass,
        config_entry=entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="test-localhost:123:1",
        subentry=subentry,
    )


@pytest.mark.parametrize(
    ("host", "entity_id", "expected"),
    [
        ("127.0.0.1", "sensor.127001_firmware_version", "sensor.firmware_version"),
        ("localhost", "sensor.localhost_power", "sensor.power"),
        ("127.0.0.1", "sensor.firmware_version", None),
        ("127.0.0.1", "sensor.my_own_name", None),
    ],
    ids=["forced_id", "hostname", "already_legacy", "user_named"],
)
def test_get_legacy_entity_id(host: str, entity_id: str, expected: str | None) -> None:
    """Only an id this integration forced is recognised as one to restore.

    Anything the user named themselves is left alone: the restore is not a licence
    to rename entities.
    """
    assert get_legacy_entity_id(entity_id, host) == expected


@pytest.mark.asyncio
async def test_setting_up_never_renames_an_existing_entity(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """An entity keeps the id it has, however often the entry is set up.

    The unique id is what Home Assistant matches on, so an entity registered
    under a name of the user's choosing stays under it.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    entity = _entity(hass, entry, "sensor.my_own_name")
    entity_id = entity.entity_id
    registry = er.async_get(hass)

    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(connected=True),
        ),
        patch(
            "custom_components.modbus_local_gateway.helpers.async_setup_entities",
            MagicMock(),
        ),
    ):
        for _ in range(2):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

    kept = registry.async_get(entity_id)
    assert kept is not None
    assert kept.entity_id == "sensor.my_own_name"


@pytest.mark.asyncio
async def test_legacy_entity_ids_are_only_suggested(hass: HomeAssistant) -> None:
    """An entity created in the legacy style is not given the host prefix.

    The host prefix was the forced rename of #168. An entry that has it switched
    off asks for it: the suggestion only applies to entities created from here on,
    which is what the option says it does.
    """
    for legacy, expected in (
        (True, None),
        (False, "sensor.localhost_firmware_version"),
    ):
        entry = mock_gateway_entry(legacy_entity_ids=legacy)
        entry.add_to_hass(hass)
        entity = ModbusCoordinatorEntity(
            coordinator=_coordinator(hass, entry),
            ctx=ModbusContext(device_id=1, desc=DESCRIPTION),
            device=MagicMock(),
        )
        assert entity.entity_id == expected
        # The unique id is the identity of the entity and never changes.
        assert entity.unique_id == "test-1-firmware_version"


@pytest.mark.asyncio
async def test_prefixed_entity_ids_is_the_default(hass: HomeAssistant) -> None:
    """A gateway added from now on names its entities after the gateway.

    An upgrade does not follow this default: the migration writes `True`
    explicitly, so a gateway that came from before one-entry-per-gateway stays
    on the ids it had and is still offered the one-click restore. See
    `CONF_MIGRATED_LEGACY_ENTITY_IDS`.
    """
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)
    assert entry.data[CONF_LEGACY_ENTITY_IDS] == CONF_LEGACY_ENTITY_IDS_DEFAULT
    assert CONF_LEGACY_ENTITY_IDS_DEFAULT is False


@pytest.mark.asyncio
async def test_restore_puts_the_old_entity_ids_back(
    hass: HomeAssistant,
) -> None:
    """The ids of v2026.02.0 are restored when the user asks for it."""
    entry = mock_gateway_entry(legacy_entity_ids=True)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    _entity(hass, entry, "sensor.localhost_firmware_version")

    restored = await async_restore_legacy_entity_ids(hass, entry)

    assert restored == 1
    assert registry.async_get("sensor.firmware_version") is not None
    assert registry.async_get("sensor.localhost_firmware_version") is None


@pytest.mark.asyncio
async def test_restore_keeps_the_unique_id_and_the_device(
    hass: HomeAssistant,
) -> None:
    """Restoring an entity id does not recreate the entity.

    The id changes, so anything pointing at the entity by unique id or device has
    to keep working - that is the whole point of restoring rather than deleting
    and recreating.
    """
    entry = mock_gateway_entry(legacy_entity_ids=True)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        config_subentry_id=entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE)[
            0
        ].subentry_id,
        identifiers={(DOMAIN, "test-localhost:123:1")},
        name="test slave 1",
    )
    original = _entity(
        hass, entry, "sensor.localhost_firmware_version", device_id=device.id
    )
    hass.states.async_set(
        original.entity_id, "1.0", {"friendly_name": "Firmware version"}
    )
    await hass.async_block_till_done()
    history = original.id

    await async_restore_legacy_entity_ids(hass, entry)

    restored = registry.async_get("sensor.firmware_version")
    assert restored is not None
    assert restored.id == history
    assert restored.unique_id == original.unique_id
    assert restored.device_id == device.id
    assert restored.config_subentry_id == original.config_subentry_id


@pytest.mark.asyncio
async def test_restore_leaves_a_taken_entity_id_alone(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """An id another entity already uses is not taken from it."""
    entry = mock_gateway_entry(legacy_entity_ids=True)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    _entity(hass, entry, "sensor.localhost_firmware_version")
    other = MockConfigEntry(domain=DOMAIN, data=gateway_data(), version=2)
    other.add_to_hass(hass)
    registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        "other",
        config_entry=other,
        suggested_object_id="firmware_version",
    )

    restored = await async_restore_legacy_entity_ids(hass, entry)

    assert restored == 0
    assert registry.async_get("sensor.localhost_firmware_version") is not None


@pytest.mark.asyncio
async def test_restore_only_touches_its_own_entities(hass: HomeAssistant) -> None:
    """An entity of another gateway is not renamed by this one."""
    entry = mock_gateway_entry(legacy_entity_ids=True)
    entry.add_to_hass(hass)
    other = mock_gateway_entry(host="10.0.0.9", legacy_entity_ids=True)
    other.add_to_hass(hass)
    _entity(hass, entry, "sensor.localhost_firmware_version")
    untouched = _entity(hass, other, "sensor.localhost_power")

    await async_restore_legacy_entity_ids(hass, entry)

    assert er.async_get(hass).async_get(untouched.entity_id) is not None


@pytest.mark.asyncio
async def test_setup_does_not_restore_entity_ids(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """Setting an entry up never renames anything, not even a forced id.

    This is the behaviour of #168: the entity id is the user's to change.
    """
    entry = mock_gateway_entry()
    entry.add_to_hass(hass)
    _entity(hass, entry, "sensor.localhost_firmware_version")

    with (
        patch(
            "custom_components.modbus_local_gateway."
            "AsyncModbusTcpClientGateway.async_get_client_connection",
            return_value=MagicMock(connected=True),
        ),
        patch(
            "custom_components.modbus_local_gateway.helpers.async_setup_entities",
            MagicMock(),
        ),
        patch(
            "custom_components.modbus_local_gateway.config_flow"
            ".async_restore_legacy_entity_ids",
            MagicMock(side_effect=AssertionError("restore during setup")),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert er.async_get(hass).async_get("sensor.localhost_firmware_version") is not None


@pytest.mark.asyncio
async def test_restore_is_reachable_only_from_the_gateway_form(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """The restore is offered by the gateway, the thing that owns the host.

    A gateway added from now on is not on legacy ids and is never given them, so
    it is not offered a restore of ids it does not have. Only a gateway that is
    on them is.
    """
    entry = mock_gateway_entry(legacy_entity_ids=True)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    fields = {str(key.schema) for key in result["data_schema"].schema}
    assert CONF_RESTORE_ENTITY_IDS in fields
    assert CONF_HOST in fields
    assert CONF_PORT in fields


@pytest.mark.asyncio
async def test_new_gateway_is_not_offered_a_restore(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A gateway added from now on is not offered a restore of ids it never had."""
    entry = mock_gateway_entry(legacy_entity_ids=CONF_LEGACY_ENTITY_IDS_DEFAULT)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    fields = {str(key.schema) for key in result["data_schema"].schema}
    assert CONF_RESTORE_ENTITY_IDS not in fields


@pytest.mark.asyncio
async def test_subentry_flow_does_not_offer_a_restore(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    """A device cannot restore entity ids: the host prefix is not its business."""
    entry = mock_gateway_entry(slave_ids=[])
    entry.add_to_hass(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE),
        context=SubentryFlowContext(source=SOURCE_USER),
    )
    assert result["data_schema"] is not None
    fields = {str(key.schema) for key in result["data_schema"].schema}
    assert CONF_RESTORE_ENTITY_IDS not in fields


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control_type", "key", "expected"),
    [
        (
            Platform.NUMBER,
            "GridFirstDischargePowerRate",
            "localhost_gridfirstdischargepowerrate",
        ),
        (Platform.SWITCH, "AcChargeEnable", "localhost_acchargeenable"),
        (Platform.NUMBER, "BatFirstStopSOC", "localhost_batfirststopsoc"),
        # A key that is already a slug is left exactly as it is, so the ids of
        # the entities that already exist do not change.
        (Platform.SENSOR, "firmware_version", "localhost_firmware_version"),
    ],
    ids=["number", "switch", "soc", "already_a_slug"],
)
async def test_a_camel_case_key_makes_a_valid_entity_id(
    hass: HomeAssistant,
    control_type: Platform,
    key: str,
    expected: str,
) -> None:
    """A yaml key that is not a slug still gives a valid entity id.

    An object id has to be a slug. `GridFirstDischargePowerRate` is not one, and
    Home Assistant warns for every entity that sets such an id, and stops
    accepting them in 2027.2.0.
    """
    entry = mock_gateway_entry(legacy_entity_ids=False)
    entry.add_to_hass(hass)
    entity = ModbusCoordinatorEntity(
        coordinator=_coordinator(hass, entry),
        ctx=ModbusContext(
            device_id=1,
            desc=_description(key, control_type),
        ),
        device=MagicMock(),
    )

    assert entity.entity_id == f"{control_type}.{expected}"
    assert valid_entity_id(entity.entity_id)


@pytest.mark.asyncio
async def test_a_camel_case_key_does_not_change_the_unique_id(
    hass: HomeAssistant,
) -> None:
    """The unique id still spells the key as the yaml does.

    The unique id is how an entity is recognised in the registry, so changing it
    would make every entity of a CamelCase device a new entity, orphaning the one
    it replaces.
    """
    entry = mock_gateway_entry(legacy_entity_ids=False)
    entry.add_to_hass(hass)
    entity = ModbusCoordinatorEntity(
        coordinator=_coordinator(hass, entry),
        ctx=ModbusContext(
            device_id=1,
            desc=_description("GridFirstStopSOC"),
        ),
        device=MagicMock(),
    )

    assert entity.unique_id == "test-1-GridFirstStopSOC"
