"""The Modbus Local Gateway sensor integration."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import logging
from types import MappingProxyType
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import (
    CONF_FILENAME,
    CONF_HOST,
    CONF_PORT,
    Platform,
)
from homeassistant.const import (
    __version__ as HA_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CONNECTION_TYPE,
    CONF_DEFAULT_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_LEGACY_ENTITY_IDS,
    CONF_MIGRATED_LEGACY_ENTITY_IDS,
    CONF_PREFIX,
    DOMAIN,
    MIN_HOMEASSISTANT_VERSION,
    OPTIONS_DEFAULT_EXPECTED_OFFLINE,
    OPTIONS_DEFAULT_REFRESH,
    OPTIONS_DEFAULT_WRITE_FUNCTION,
    OPTIONS_EXPECTED_OFFLINE,
    OPTIONS_REFRESH,
    OPTIONS_WRITE_FUNCTION,
    PLATFORMS,
    SUBENTRY_TYPE_DEVICE,
)
from .coordinator import ModbusCoordinator
from .entity_management.base import ModbusEntityDescription
from .entity_management.const import ControlType
from .entity_management.device_loader import create_device_info
from .helpers import (
    GATEWAY_DEVICE_KEY,
    get_connection_key,
    get_connection_type,
    get_device_config,
    get_device_identifiers,
    get_device_key,
    get_device_title,
    get_gateway_device_identifier,
    is_supported_home_assistant,
)
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Nothing is configured in YAML: every gateway is a config entry the flow
# creates. `async_setup` only prepares the entries a previous version wrote.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass(slots=True)
class GatewayRuntime:
    """What a loaded gateway entry keeps in memory.

    The client is kept next to the coordinators instead of being looked up
    again on unload: the settings of the entry can have changed since setup,
    and a gateway may have no devices at all.
    """

    client: AsyncModbusTcpClientGateway
    coordinators: dict[str, ModbusCoordinator] = field(default_factory=dict)


# Version 1 was one config entry per device; version 2 is one config entry per
# gateway connection, holding one config sub-entry per device behind it.
ENTRY_VERSION = 2


def _unsupported_version_error() -> ConfigEntryError:
    """Return the error shown when Home Assistant is too old."""
    return ConfigEntryError(
        translation_domain=DOMAIN,
        translation_key="unsupported_home_assistant_version",
        translation_placeholders={
            "current_version": HA_VERSION,
            "min_version": MIN_HOMEASSISTANT_VERSION,
        },
    )


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the integration and prepare entries created before sub-entries.

    Nothing is configured in YAML: the flow creates the entries, and entries
    created before this release are prepared here.
    """
    if is_supported_home_assistant():
        await _async_migrate_entries(hass)
        await _async_migrate_device_titles(hass)
    else:
        # Every entry reports the same translated error while it is set up, so
        # there is nothing to migrate (or repair) on this version.
        _LOGGER.error(
            "Home Assistant %s is older than the required %s",
            HA_VERSION,
            MIN_HOMEASSISTANT_VERSION,
        )
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up the gateway connection and every device behind it."""
    if not is_supported_home_assistant():
        raise _unsupported_version_error()

    device_registry: dr.DeviceRegistry = dr.async_get(hass)
    connection_type: str = get_connection_type(entry.data)
    connection_key: str = get_connection_key(entry.data)

    client: AsyncModbusTcpClientGateway | None = (
        AsyncModbusTcpClientGateway.async_get_client_connection(
            host=entry.data[CONF_HOST],
            port=entry.data[CONF_PORT],
            connection_type=connection_type,
        )
    )
    if client is None:
        raise ConfigEntryNotReady(f"Unable to connect to {connection_key}")

    gateway_device: dr.DeviceEntry | None = None
    if connection_type == CONF_DEFAULT_CONNECTION_TYPE:
        gateway_device = _setup_gateway_device(entry, device_registry)

    runtime = GatewayRuntime(client=client)
    for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE):
        config: dict[str, Any] = get_device_config(entry, subentry)
        try:
            device_info = await hass.async_add_executor_job(
                create_device_info, hass, config[CONF_FILENAME]
            )
        except FileNotFoundError:
            # The device file of this device alone is gone. The other devices
            # behind the gateway are unaffected by that, so this one is skipped
            # instead of taking the whole gateway down with it.
            _LOGGER.error(
                "Device file %s of %s not found, skipping the device",
                config[CONF_FILENAME],
                subentry.title,
            )
            continue

        coordinator = ModbusCoordinator(
            hass=hass,
            config_entry=entry,
            gateway_device=gateway_device,
            client=client,
            gateway=get_device_key(config),
            update_interval=subentry.data.get(OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH),
            subentry=subentry,
            device_info=device_info,
        )
        coordinator.max_read_size = device_info.max_read_size
        runtime.coordinators[subentry.subentry_id] = coordinator

    entry.runtime_data = runtime
    _setup_device_devices(entry, device_registry, gateway_device)
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    _async_move_composite_entity_ids(hass, entry, runtime)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for coordinator in runtime.coordinators.values():
        # Only now are the entities registered with their coordinator, so this is
        # the first point where the device can be read as a whole. Reading it any
        # earlier would be Home Assistant waiting, during setup, for the reads of
        # devices that may well be switched off.
        coordinator.async_schedule_initial_poll()
    return True


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after devices were added, changed or removed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Entities are still loaded. Closing the client below would pull the
        # connection out from under them, so leave everything in place.
        return False

    runtime: GatewayRuntime = entry.runtime_data
    client: AsyncModbusTcpClientGateway = runtime.client
    for coordinator in runtime.coordinators.values():
        # The first poll is still outstanding for every device that has not been
        # read yet, and it is holding on to the client: drop it before the client
        # goes away.
        coordinator.async_cancel_initial_poll()
    runtime.coordinators.clear()

    # The client is cached per host/port/framer and shared by every entry
    # pointing at the same gateway, so it can only be closed once no other
    # loaded entry is using it. Leaving it open keeps the socket - and pymodbus'
    # retries - alive after the entry is gone.
    if {client}.isdisjoint(_async_clients_in_use(hass, entry.entry_id)):
        client.close_cached()

    return True


def _async_clients_in_use(
    hass: HomeAssistant, entry_id: str
) -> set[AsyncModbusTcpClientGateway]:
    """Return the clients used by every other loaded config entry."""
    clients: set[AsyncModbusTcpClientGateway] = set()
    for other in hass.config_entries.async_loaded_entries(DOMAIN):
        if other.entry_id == entry_id:
            continue
        runtime_data = getattr(other, "runtime_data", None)
        if isinstance(runtime_data, GatewayRuntime):
            clients.update(
                coordinator.client for coordinator in runtime_data.coordinators.values()
            )
    return clients


def _setup_gateway_device(
    entry: ConfigEntry, device_registry: dr.DeviceRegistry
) -> dr.DeviceEntry:
    """Create the device of the gateway connection itself.

    The gateway device is owned by the config entry, not by a sub-entry: it
    represents the connection the entry configures, not one of the devices
    behind it. Devices cannot be linked to a sub-entry from an entity, so the
    sub-entry devices are created here as well.
    """
    gateway_identifier: str = get_gateway_device_identifier(entry.data)
    connection_key: str = get_connection_key(entry.data)
    gateway_device: dr.DeviceEntry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, gateway_identifier)},
        name=f"Modbus Gateway ({connection_key})",
        configuration_url=f"http://{entry.data[CONF_HOST]}/",
    )

    return gateway_device


def _async_move_composite_entity_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    runtime: GatewayRuntime,
) -> int:
    """Move the `datetime` entities that are a time or a date onto their platform.

    A `time` or `date` composite used to be built as a `datetime` entity whose
    value was a date and a time with today's date on it, which was not a reading
    of the device. Each is now exposed on the platform that says what it is, and
    an entity's registry key is (domain, platform, unique id): so an entity that
    changes platform is a *different* registry entry, and leaving the old one
    behind would leave it registered for ever with nothing to write to it. It is
    therefore moved here, while the coordinators are built and before any
    platform is set up.

    The registry will not rename an entity onto another platform - it refuses a
    new entity id whose domain differs - so the entry is built on its platform
    and the old one dropped, carrying over what the user set on it. The object
    id is kept, so only the platform in front of it changes; the recorder holds
    the old entity id's history, which does not follow an entity to another
    platform. Nothing else is touched: a `datetime` composite stays a
    `datetime`, and no entity of another platform is touched. Runs on every setup
    and does nothing once it has been done, so it needs no entry version of its
    own.
    """
    entity_registry: er.EntityRegistry = er.async_get(hass)
    # The platform each entity of this entry now belongs on, by unique id.
    # `control_type` is declared as a plain str, so this is one too.
    descriptions: dict[str, str] = {}
    for coordinator in runtime.coordinators.values():
        for desc in coordinator.device_info.entity_descriptions:
            registered_id: str | None = _entity_unique_id(coordinator, desc)
            if registered_id is not None and desc.control_type is not None:
                descriptions[registered_id] = desc.control_type

    moved: int = 0
    for entity_entry in tuple(entity_registry.entities.values()):
        if (
            entity_entry.config_entry_id != entry.entry_id
            or entity_entry.domain != Platform.DATETIME
            or entity_entry.unique_id is None
        ):
            continue
        control_type: str | None = descriptions.get(entity_entry.unique_id)
        if control_type not in (ControlType.TIME, ControlType.DATE):
            continue
        object_id: str = entity_entry.entity_id.split(".", 1)[1]
        new_entry = entity_registry.async_get_or_create(
            control_type,
            DOMAIN,
            entity_entry.unique_id,
            config_entry=entry,
            config_subentry_id=entity_entry.config_subentry_id,
            device_id=entity_entry.device_id,
            suggested_object_id=object_id,
        )
        # Everything the user decided about the entity - where it sits, what it
        # is called, what it looks like, whether it is shown at all - has to be
        # set again on the new entry, which starts from the defaults. The
        # values the device config supplies are left out: the new platform
        # sets those itself when it registers the entity.
        entity_registry.async_update_entity(
            new_entry.entity_id,
            aliases=entity_entry.aliases,
            area_id=entity_entry.area_id,
            categories=entity_entry.categories,
            disabled_by=entity_entry.disabled_by,
            entity_category=entity_entry.entity_category,
            hidden_by=entity_entry.hidden_by,
            icon=entity_entry.icon,
            labels=entity_entry.labels,
            name=entity_entry.name,
        )
        for domain, domain_options in entity_entry.options.items():
            entity_registry.async_update_entity_options(
                new_entry.entity_id, domain, dict(domain_options)
            )
        entity_registry.async_remove(entity_entry.entity_id)
        _LOGGER.info(
            "Moved %s to %s: a %s is not a date and a time",
            entity_entry.entity_id,
            new_entry.entity_id,
            control_type,
        )
        moved += 1
    return moved


def _entity_unique_id(
    coordinator: ModbusCoordinator, desc: ModbusEntityDescription
) -> str | None:
    """The unique id an entity of `desc` is registered under.

    Built the same way `ModbusCoordinatorEntity` builds it, so an entity can be
    found from the descriptions rather than by taking its key apart again. None
    for a coordinator with no device id, which has no entities registered under
    one either.
    """
    device_id: int | None = coordinator.device_id
    if device_id is None:
        return None
    prefix: str | None = coordinator.prefix
    return f"{prefix}-{device_id}-{desc.key}" if prefix else f"{device_id}-{desc.key}"


def _setup_device_devices(
    entry: ConfigEntry,
    device_registry: dr.DeviceRegistry,
    gateway_device: dr.DeviceEntry | None,
) -> None:
    """Create the device of every device behind the gateway.

    A `DeviceInfo` cannot say which config sub-entry a device belongs to, so
    entities created later can only find their device by its identifiers.
    """
    for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE):
        coordinator: ModbusCoordinator | None = entry.runtime_data.coordinators.get(
            subentry.subentry_id
        )
        if coordinator is None:
            # Setup skipped this device, so there is nothing to register.
            continue

        config: dict[str, Any] = get_device_config(entry, subentry)
        device_info = coordinator.device_info

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            identifiers=get_device_identifiers(config),
            name=" ".join(
                part for part in [config.get(CONF_PREFIX), device_info.model] if part
            ),
            manufacturer=device_info.manufacturer,
            model=device_info.model,
            via_device_id=gateway_device.id if gateway_device else None,
        )

    _LOGGER.debug("Devices ready for %d sub-entries", len(entry.subentries))


def _connection_group_key(entry: ConfigEntry) -> tuple[str, int, str]:
    """Return what entries sharing one gateway connection have in common."""
    return (
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        get_connection_type(entry.data),
    )


def _device_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return the settings of the device a version 1 entry described."""
    data: dict[str, Any] = {
        CONF_PREFIX: entry.data.get(CONF_PREFIX, ""),
        CONF_DEVICE_ID: entry.data[CONF_DEVICE_ID],
        CONF_FILENAME: entry.data[CONF_FILENAME],
        OPTIONS_REFRESH: entry.options.get(OPTIONS_REFRESH, OPTIONS_DEFAULT_REFRESH),
        OPTIONS_WRITE_FUNCTION: entry.options.get(
            OPTIONS_WRITE_FUNCTION, OPTIONS_DEFAULT_WRITE_FUNCTION
        ),
        OPTIONS_EXPECTED_OFFLINE: entry.options.get(
            OPTIONS_EXPECTED_OFFLINE, OPTIONS_DEFAULT_EXPECTED_OFFLINE
        ),
    }
    return data


def _legacy_device_title(config: Mapping[str, Any]) -> str:
    """Return the title a device sub-entry was given before 2026.10.1.

    This is the only title the integration wrote itself, so it is what the
    migration matches on: a title that is anything else was set by the user or
    comes from a later version, and is left alone.
    """
    prefix: str = config.get(CONF_PREFIX) or ""
    return f"{prefix + ' ' if prefix else ''}slave {config[CONF_DEVICE_ID]}"


async def _async_migrate_device_titles(hass: HomeAssistant) -> None:
    """Rename the device sub-entries still carrying the old "slave N" title.

    The title is written when a device is created and refreshed when it is
    reconfigured, so a device set up before 2026.10.1 keeps saying "slave 2" in
    the list of devices behind its gateway until it is saved again. Only the
    titles this integration wrote itself are rewritten, so a device a user has
    renamed keeps the name they gave it.
    """
    renamed: int = 0
    for entry in hass.config_entries.async_entries(DOMAIN):
        for subentry in entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE):
            config: dict[str, Any] = get_device_config(entry, subentry)
            # Compared case-insensitively: a sub-entry title can come back with
            # its first letter capitalised, so an exact match would miss it and
            # the device would keep the name it was given to shed.
            if subentry.title.casefold() != _legacy_device_title(config).casefold():
                continue
            # The return value is what says the title was really written, so it
            # is what is counted: an update that changed nothing is not a rename.
            if hass.config_entries.async_update_subentry(
                entry, subentry, title=get_device_title(config)
            ):
                renamed += 1

    if renamed:
        _LOGGER.info("Renamed %d device sub-entries by their device id", renamed)


async def _async_migrate_entries(hass: HomeAssistant) -> None:
    """Rewrite version 1 entries as one entry per gateway connection.

    Everything that identifies an entity, a device or a config entry stays as it
    is: entity ids, unique ids, device ids, areas and dashboard customizations
    all keep working, and nothing is renamed.
    """
    entries: list[ConfigEntry] = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.version < ENTRY_VERSION
    ]
    if not entries:
        return

    _LOGGER.info("Migrating %d config entries to sub-entries", len(entries))

    groups: dict[tuple[str, int, str], list[ConfigEntry]] = {}
    for entry in entries:
        groups.setdefault(_connection_group_key(entry), []).append(entry)

    device_registry: dr.DeviceRegistry = dr.async_get(hass)
    entity_registry: er.EntityRegistry = er.async_get(hass)

    for group in groups.values():
        await _async_migrate_group(hass, device_registry, entity_registry, group)


async def _async_migrate_group(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    group: list[ConfigEntry],
) -> None:
    """Rewrite the entries of one gateway connection as one entry."""
    # Enabled entries first: a group is merged into the entry that survives,
    # and a disabled entry must not disable the devices of an enabled one.
    survivors = sorted(group, key=lambda entry: entry.disabled_by is not None)
    parent: ConfigEntry = survivors[0]
    all_disabled: bool = all(entry.disabled_by is not None for entry in group)

    for entry in group:
        config: dict[str, Any] = {**entry.data, **_device_data(entry)}
        parent, subentry = _async_add_device_subentry(hass, parent, entry)
        _async_move_device_to_subentry(
            device_registry,
            entity_registry,
            parent_id=parent.entry_id,
            entry=entry,
            subentry=subentry,
            config=config,
            all_disabled=all_disabled,
        )

    _async_normalise_gateway_devices(
        device_registry, entity_registry, parent, group, all_disabled
    )

    hass.config_entries.async_update_entry(
        parent,
        data={
            CONF_HOST: parent.data[CONF_HOST],
            CONF_PORT: parent.data[CONF_PORT],
            CONF_CONNECTION_TYPE: get_connection_type(parent.data),
            CONF_LEGACY_ENTITY_IDS: CONF_MIGRATED_LEGACY_ENTITY_IDS,
        },
        options={},
        title=f"Modbus Gateway ({get_connection_key(parent.data)})",
        version=ENTRY_VERSION,
    )

    for entry in group:
        if entry.entry_id == parent.entry_id:
            continue
        if _entry_owns_nothing(device_registry, entity_registry, entry.entry_id):
            await hass.config_entries.async_remove(entry.entry_id)
        else:
            # Keep the entry: removing it would detach devices and entities
            # that could not be moved, losing their history.
            _LOGGER.warning(
                "Keeping config entry %s: it still owns registry items",
                entry.entry_id,
            )


def _async_add_device_subentry(
    hass: HomeAssistant, parent: ConfigEntry, entry: ConfigEntry
) -> tuple[ConfigEntry, ConfigSubentry]:
    """Add the device of a version 1 entry as a sub-entry of its gateway.

    Adding a sub-entry replaces the sub-entries the config entry holds, so the
    entry is read back from the registry afterwards: everything that follows
    works on the entry as it is now, not as it was handed in.
    """
    config: dict[str, Any] = {**entry.data, **_device_data(entry)}
    unique_id: str = get_device_key(config)
    parent = hass.config_entries.async_get_entry(parent.entry_id) or parent

    subentry: ConfigSubentry | None = next(
        (known for known in parent.subentries.values() if known.unique_id == unique_id),
        None,
    )
    if subentry is not None:
        return parent, subentry

    subentry = ConfigSubentry(
        data=MappingProxyType(_device_data(entry)),
        subentry_type=SUBENTRY_TYPE_DEVICE,
        title=get_device_title(config),
        unique_id=unique_id,
    )
    hass.config_entries.async_add_subentry(parent, subentry)
    parent = hass.config_entries.async_get_entry(parent.entry_id) or parent
    return parent, subentry


def _entry_owns_nothing(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    entry_id: str,
) -> bool:
    """Return whether a config entry no longer owns devices or entities."""
    return not dr.async_entries_for_config_entry(
        device_registry, entry_id
    ) and not er.async_entries_for_config_entry(entity_registry, entry_id)


def _async_move_device_to_subentry(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    parent_id: str,
    entry: ConfigEntry,
    subentry: ConfigSubentry,
    config: Mapping[str, Any],
    all_disabled: bool,
) -> None:
    """Move the devices and entities of one entry into one sub-entry.

    The entities move first, because Home Assistant deletes the entities of a
    device that moves into a sub-entry while they still point at the old one:
    that would throw away the entity ids, and with them the history, of every
    entity of the device.

    Neither registry adjusts `disabled_by` when a registry item moves into a
    sub-entry, so an item disabled because its config entry was disabled is
    disabled by the user now: the sub-entry, and with it the entry, is still
    enabled.
    """
    device: dr.DeviceEntry | None = None
    for identifier in get_device_identifiers(config):
        device = device_registry.async_get_device_by_identifier(
            identifier, entry.entry_id
        )
        if device is not None:
            break

    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, entry.entry_id
    ):
        entity_registry.async_update_entity(
            entity_entry.entity_id,
            config_entry_id=parent_id,
            config_subentry_id=subentry.subentry_id,
            disabled_by=_entity_disabled_by(entity_entry, device, all_disabled),
        )

    if device is not None:
        device_registry.async_update_device(
            device.id,
            disabled_by=_device_disabled_by(device, all_disabled),
            new_config_entry_id=parent_id,
            new_config_subentry_id=subentry.subentry_id,
        )


def _device_disabled_by(
    device: dr.DeviceEntry, all_disabled: bool
) -> dr.DeviceEntryDisabler | None:
    """Return the disabled_by a moved device should have."""
    if device.disabled_by is dr.DeviceEntryDisabler.CONFIG_ENTRY and not all_disabled:
        return dr.DeviceEntryDisabler.USER
    return device.disabled_by


def _entity_disabled_by(
    entity_entry: er.RegistryEntry,
    device: dr.DeviceEntry | None,
    all_disabled: bool,
) -> er.RegistryEntryDisabler | None:
    """Return the disabled_by a moved entity should have."""
    if (
        entity_entry.disabled_by is er.RegistryEntryDisabler.CONFIG_ENTRY
        and not all_disabled
    ):
        return (
            er.RegistryEntryDisabler.DEVICE if device else er.RegistryEntryDisabler.USER
        )
    return entity_entry.disabled_by


def _async_normalise_gateway_devices(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    parent: ConfigEntry,
    entries: Iterable[ConfigEntry],
    all_disabled: bool,
) -> None:
    """Give the gateway device its version 2 identifier.

    Version 1 put the prefix of the device in front of the gateway device
    identifier, so one connection could have a gateway device per device behind
    it - one per config entry, to be exact. Those are merged into the single
    device the connection now has. The identifier does not change for anybody's
    device id, area or dashboard: the registry renames the identifiers of the
    device in place.

    Every entry of the group is looked at, not just the one that survives: a
    duplicate keeps its gateway device otherwise, and an entry that owns
    anything is kept rather than removed.
    """
    target: tuple[str, str] = (DOMAIN, get_gateway_device_identifier(parent.data))
    gateway_prefix: str = f"{GATEWAY_DEVICE_KEY}-"

    candidates: list[dr.DeviceEntry] = []
    for entry in entries:
        candidates.extend(
            dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        )

    # The device of the entry that survives is kept, so that the duplicates are
    # the ones of the entries that are about to go. The id breaks a tie, to keep
    # the outcome the same on every run: the registry hands out ids at random.
    keeper: dr.DeviceEntry | None = None
    for device in sorted(
        candidates,
        key=lambda device: (device.config_entry_id != parent.entry_id, device.id),
    ):
        if not _is_gateway_device(device, gateway_prefix):
            continue
        if keeper is None:
            keeper = device
            continue
        for child in candidates:
            if child.via_device_id == device.id:
                device_registry.async_update_device(child.id, via_device_id=keeper.id)
        _async_merge_gateway_device(device_registry, entity_registry, keeper, device)

    if keeper is None:
        return

    device_registry.async_update_device(
        keeper.id,
        disabled_by=_device_disabled_by(keeper, all_disabled),
        new_identifiers={
            identifier
            for identifier in keeper.identifiers
            if not (
                identifier[0] == DOMAIN and identifier[1].startswith(gateway_prefix)
            )
        }
        | {target},
        new_config_entry_id=parent.entry_id,
    )


def _is_gateway_device(device: dr.DeviceEntry, gateway_prefix: str) -> bool:
    """Return whether a device is a version 1 gateway device."""
    return any(
        domain == DOMAIN and identifier.startswith(gateway_prefix)
        for domain, identifier in device.identifiers
    )


def _async_merge_gateway_device(
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    keeper: dr.DeviceEntry,
    duplicate: dr.DeviceEntry,
) -> None:
    """Move the entities of a duplicate gateway device onto the one kept.

    A gateway device has no entities of its own, so this is normally a no-op. It
    is not assumed: a user can have attached one, and dropping it with the device
    would lose it.
    """
    entities: Iterable[er.RegistryEntry] = (
        entity_registry.entities.get_entries_for_device_id(duplicate.id)
    )
    for entity_entry in entities:
        entity_registry.async_update_entity(entity_entry.entity_id, device_id=keeper.id)
    _LOGGER.debug("Removing duplicate gateway device %s", duplicate.id)
    device_registry.async_remove_device(duplicate.id)
