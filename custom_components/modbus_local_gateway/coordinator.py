"""Representation of Modbus Gateway"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
import logging
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_HOST, EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import (
    CALLBACK_TYPE,
    CoreState,
    Event,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from pymodbus.pdu.pdu import ModbusPDU

from .composite import CompositeConversion
from .const import (
    CONF_DEVICE_ID,
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_PREFIX,
    OPTIONS_DEFAULT_EXPECTED_OFFLINE,
    OPTIONS_DEFAULT_WRITE_FUNCTION,
    OPTIONS_EXPECTED_OFFLINE,
    OPTIONS_WRITE_FUNCTION,
)
from .context import ModbusContext
from .conversion import Conversion, ValueUnavailable
from .entity_management.base import (
    ModbusCompositeEntityDescription,
    ModbusEntityDescription,
)
from .entity_management.const import WriteFunction
from .entity_management.modbus_device_info import ModbusDeviceInfo
from .exceptions import ModbusNoResponseError
from .tcp_client import AsyncModbusTcpClientGateway, DevicePolicy

_LOGGER: logging.Logger = logging.getLogger(__name__)

# A poll that has not finished by now is abandoned. This is a backstop, not the
# mechanism that bounds a poll: a device that stops answering ends its cycle at
# the first unanswered read, which is a handful of seconds. What is left to
# catch is a poll waiting on the shared client lock for longer than any real
# device could need, which would otherwise hold that lock indefinitely.
_POLL_BACKSTOP: float = 120.0

__all__ = [
    "ModbusContext",
    "ModbusCoordinator",
    "ModbusCoordinatorEntity",
    "async_restore_legacy_entity_ids",
    "get_host_object_id",
    "get_legacy_entity_id",
]


def get_host_object_id(host: str) -> str:
    """Return the object id prefix v2026.02.0 forced onto existing entities.

    IP/Host without separators (e.g. 192.168.1.10 -> 192168110).
    """
    return str(host).replace(".", "").replace(":", "").replace("-", "").replace(" ", "")


def get_legacy_entity_id(entity_id: str, host: str) -> str | None:
    """Return the entity id v2026.02.0 forced for an entity, if it has one.

    Only an entity id this integration created is recognised, so nothing the
    user named themselves is ever returned.
    """
    domain, _, object_id = entity_id.partition(".")
    forced_prefix = f"{get_host_object_id(host)}_"
    if object_id.startswith(forced_prefix):
        return f"{domain}.{object_id[len(forced_prefix) :]}"
    return None


async def async_restore_legacy_entity_ids(
    hass: HomeAssistant, entry: ConfigEntry
) -> int:
    """Restore the entity ids v2026.02.0 forced onto existing entities.

    Only ever called from a form the user confirmed, never while setting up:
    #168 is about this integration renaming entities behind the user's back, so
    changing an entity id has to be their decision. Returns the number of
    entities that were renamed.
    """
    if not entry.data.get(CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT):
        return 0

    entity_registry: er.EntityRegistry = er.async_get(hass)
    restored: int = 0
    # Renaming moves an entity to another key in the registry, so the entities to
    # look at are collected before any of them is touched.
    for entity_entry in tuple(entity_registry.entities.values()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        entity_id: str | None = get_legacy_entity_id(
            entity_entry.entity_id, entry.data[CONF_HOST]
        )
        if entity_id is None:
            continue
        try:
            entity_registry.async_update_entity(
                entity_entry.entity_id, new_entity_id=entity_id
            )
        except ValueError:
            # The old id is taken by another entity: keep what there is.
            _LOGGER.warning(
                "Cannot restore entity id of %s, %s is already taken",
                entity_entry.entity_id,
                entity_id,
            )
            continue
        _LOGGER.info("Restored entity id %s", entity_id)
        restored += 1

    return restored


class ModbusCoordinatorEntity(CoordinatorEntity):
    """Base class for Modbus entities"""

    entity_description: ModbusEntityDescription

    def __init__(
        self,
        coordinator: ModbusCoordinator,
        ctx: ModbusContext,
        device: DeviceInfo,
    ) -> None:
        """Initialize an entity."""
        super().__init__(coordinator, context=ctx)
        if not isinstance(ctx.desc, ModbusEntityDescription):
            raise TypeError()
        self.entity_description = ctx.desc

        prefix: str | None = None
        host_id: str | None = None

        if coordinator.config_entry:
            # The prefix is a per-device setting, so it comes from the sub-entry
            # rather than the gateway's data.
            prefix = coordinator.prefix
            host: str | None = coordinator.config_entry.data.get(CONF_HOST)

            if host:
                host_id = get_host_object_id(host)

        # This is what we WANT as the object_id: <ipnodots>_<yaml_key>. It only
        # applies to entities created from here on: Home Assistant reads it when
        # the entity is registered and never touches an entity_id again.
        # v2026.02.0 turned this suggestion into a forced rename of every existing
        # entity, which broke automations and made renaming in the UI impossible.
        # #168 rolled that back, so nothing here may ever rename an entity again,
        # and an entry that has switched the prefix off (legacy_entity_ids) keeps
        # the ids of the entities it already has.
        legacy_entity_ids: bool = bool(
            coordinator.config_entry
            and coordinator.config_entry.data.get(
                CONF_LEGACY_ENTITY_IDS, CONF_LEGACY_ENTITY_IDS_DEFAULT
            )
        )
        control_type: str = str(ctx.desc.control_type)
        if host_id and not legacy_entity_ids:
            # Home Assistant derives the suggestion from the entity name, so an
            # integration asks for a specific object id by setting entity_id.
            self.entity_id = f"{Platform(control_type)}.{host_id}_{ctx.desc.key}"

        # Keep unique_id compatible with previous releases so existing entities
        # can be renamed in-place.
        # (If you change unique_id, HA creates NEW entities instead of renaming
        # the existing ones.)
        self._attr_unique_id: str | None = (
            f"{prefix}-{ctx.device_id}-{ctx.desc.key}"
            if prefix
            else f"{ctx.device_id}-{ctx.desc.key}"
        )

        self._attr_device_info: DeviceInfo | None = device
        self.coordinator: ModbusCoordinator
        self.coordinator_context: ModbusContext
        self._update_lock = asyncio.Lock()
        self._cancel_timer: Callable[[], None] | None = None
        self._cancel_call: Callable[[], None] | None = None

    async def _read_data(self) -> bool:
        """Update the entity state, unless a read of it is already in progress.

        The lock is never waited for. It used to be waited for, with
        `asyncio.wait_for(self._update_lock.acquire(), 0.1)`, so that a cycle
        arriving during a read would skip rather than queue a second read - but
        `wait_for` runs the acquire in a task of its own, and if the deadline
        cancels this task in the same event loop iteration in which that task has
        already taken the lock, the cancellation is raised at the await inside
        `wait_for`, before the `try` that releases it. The lock is then held by
        nobody, and nothing can release it afterwards. Releasing the lock 10 ms
        before the deadline reproduced that 4 times in 300 attempts here; every
        later read of the entity then timed out at 0.1 s, each timeout was logged
        as "already in progress", and the entity silently stopped updating for the
        rest of the session. `asyncio.timeout()` around the same acquire does not
        leak - there is no task boundary for the grant to be lost across - but a
        read has no reason to wait for the lock at all: whatever holds it is a
        read of this same entity that is about to publish the value this read
        would have fetched.

        Returns whether the entity was read, so a skipped read does not go on to
        write the state machine: the read that holds the lock writes it when it
        finishes, which is the read whose value this cycle would have had.
        """
        if self._update_lock.locked():
            _LOGGER.debug("Update for entity %s is already in progress", self.name)
            return False
        async with self._update_lock:
            await self.coordinator.async_update_entity(self.coordinator_context)
        return True

    async def _async_update_write_state(self) -> None:
        """Update the entity state, and write it to the state machine if it was read."""
        if await self._read_data():
            self._handle_coordinator_update()

    async def write_data(
        self,
        value: str | float | bool | datetime | None,
    ) -> None:
        """Write data to the Modbus device"""
        try:
            await self.coordinator.client.write_data(
                self.coordinator_context,
                value,
                write_function=self.coordinator.write_function,
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to write %s to %s: %s", value, self.coordinator_context, exc
            )
            raise UpdateFailed from exc

        async with self._update_lock:
            # The device has been written, so this read-back cannot be skipped: a
            # read of this entity that was in flight may have fetched the value
            # from before the write, and while it holds the lock that stale value
            # stays in the cache - skip the read-back and the entity keeps
            # reporting it. So wait here for that read to finish, where it cannot
            # overlap with this one, and read it under the lock this task holds.
            # Nothing sets a deadline on this wait, so it is never cancelled with
            # the lock already taken (see `_read_data`).
            await self.coordinator.async_update_entity(self.coordinator_context)
            self._handle_coordinator_update()

    async def _async_update_if_not_in_progress(self, _: datetime | None = None) -> None:
        """Update the entity state if not already in progress."""
        await self._async_update_write_state()

    @callback
    def _async_schedule_future_update(self, delay: float) -> None:
        """Schedule an update in the future."""
        self._async_cancel_future_pending_update()
        self._cancel_call = async_call_later(
            self.hass, delay, self._async_update_if_not_in_progress
        )

    @callback
    def _async_cancel_future_pending_update(self) -> None:
        """Cancel a future pending update."""
        if self._cancel_call:
            self._cancel_call()
            self._cancel_call = None

    def _async_cancel_update_polling(self) -> None:
        """Cancel the polling."""
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None

    @callback
    def async_run(self) -> None:
        """Remote start entity.

        Deliberately does not read this entity. Home Assistant waits for the work
        that setup starts, and a read of a device that is not answering costs a
        timeout sequence per attempt, so one read per entity is what held startup
        up on a gateway with a powered-off device behind it. The device is read
        once as a whole instead, by `ModbusCoordinator`, after HA has started.
        """
        self._async_cancel_update_polling()
        if (
            self.coordinator_context.desc.scan_interval
            and self.coordinator_context.desc.scan_interval > 0
        ):
            self._cancel_timer = async_track_time_interval(
                self.hass,
                self._async_update_if_not_in_progress,
                timedelta(seconds=self.coordinator_context.desc.scan_interval),
            )

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.async_run()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity which will be removed."""
        await super().async_will_remove_from_hass()
        self._async_cancel_update_polling()
        self._async_cancel_future_pending_update()

    @property
    def available(self) -> bool:
        """Unavailable before the first poll, while silent, or on a non-value."""
        if not super().available:
            return False
        if not self.coordinator.initial_poll_done:
            # Nothing has been read yet, so there is no value behind this entity.
            # Reporting availability before the first poll shows it as an unknown
            # value rather than as a device that has not answered.
            return False
        if not self.coordinator.device_online:
            # A device that is not answering has nothing behind this entity, and
            # the reason it is not answering is already in the log.
            return False
        return not self.coordinator.is_unavailable(self.coordinator_context)


class ModbusCoordinator(TimestampDataUpdateCoordinator):
    """Update coordinator for modbus entries"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        gateway_device: dr.DeviceEntry | None,
        client: AsyncModbusTcpClientGateway,
        gateway: str,
        update_interval: int = 30,
        subentry: ConfigSubentry | None = None,
        device_info: ModbusDeviceInfo | None = None,
    ) -> None:
        """Initialise the coordinator"""
        self.client: AsyncModbusTcpClientGateway = client
        self._gateway: str = gateway
        self._max_read_size: int = 1
        self._gateway_device: dr.DeviceEntry | None = gateway_device
        # Entities whose most recent read was not a usable value.
        self._unavailable_keys: set[str] = set()
        # The first poll of a device covers every entity, including the ones that
        # poll on their own `scan_interval`: waiting for that timer would leave
        # them without a value until it first fires.
        self._poll_all_entities: bool = False
        self._initial_poll_done: bool = False
        self._initial_poll_scheduled: bool = False
        self._initial_poll_task: asyncio.Task[None] | None = None
        self._unsubscribe_start: CALLBACK_TYPE | None = None
        # One poll of a device at a time. The client lock only serialises the
        # devices behind one gateway; this keeps two polls of this device from
        # queueing up behind each other.
        self._poll_lock = asyncio.Lock()
        # Settings of the device this coordinator polls, from its sub-entry.
        self._subentry_data: Mapping[str, Any] = dict(subentry.data) if subentry else {}
        # Definition of the device this coordinator polls, from its YAML file.
        self._device_info: ModbusDeviceInfo | None = device_info
        # The slave id of the device this coordinator polls, read from the gateway
        # so the client can be asked whether it is answering.
        self._device_id: int | None = (
            subentry.data.get(CONF_DEVICE_ID) if subentry else None
        )

        super().__init__(
            hass,
            config_entry=config_entry,
            logger=_LOGGER,
            name=f"Modbus Coordinator - {self._gateway}",
            update_interval=timedelta(seconds=update_interval),
            update_method=self.async_update,
            always_update=True,
        )

    @property
    def device_info(self) -> ModbusDeviceInfo:
        """Return the definition of the device this coordinator polls."""
        assert self._device_info is not None
        return self._device_info

    @property
    def config(self) -> Mapping[str, Any]:
        """Return the settings of the device this coordinator polls.

        These live in the sub-entry: the gateway owns host and port, so the
        prefix that identifies this device is not on the config entry.
        """
        return self._subentry_data

    @property
    def prefix(self) -> str | None:
        """Return the prefix this device's entities and ids carry, if any."""
        return self._subentry_data.get(CONF_PREFIX) or None

    @property
    def gateway_device(self) -> dr.DeviceEntry | None:
        """Returns the gateway name"""
        return self._gateway_device

    @property
    def gateway(self) -> str:
        """Returns the gateway name"""
        return self._gateway

    @property
    def max_read_size(self) -> int:
        """Return the current max register read size"""
        return self._max_read_size

    @max_read_size.setter
    def max_read_size(self, value: int) -> None:
        """Sets the max register read size"""
        self._max_read_size = value

    @property
    def write_function(self) -> WriteFunction:
        """Return the Modbus write function this entry writes registers with.

        Defaults to preset single register (FC 0x06), which is what every
        installation used before the option existed. An unrecognised stored
        value falls back to that default rather than failing the write.
        """
        stored: Any = self._subentry_data.get(
            OPTIONS_WRITE_FUNCTION, OPTIONS_DEFAULT_WRITE_FUNCTION
        )
        try:
            return WriteFunction(stored)
        except ValueError:
            _LOGGER.warning(
                "Unknown write function %s for %s, using %s",
                stored,
                self._gateway,
                OPTIONS_DEFAULT_WRITE_FUNCTION,
            )
            return WriteFunction(OPTIONS_DEFAULT_WRITE_FUNCTION)

    @property
    def initial_poll_done(self) -> bool:
        """Whether the device has been read at least once."""
        return self._initial_poll_done

    @property
    def device_online(self) -> bool:
        """Whether the device answered its last read.

        Asked of the client rather than kept here, because the client is where the
        answer is: it holds what is known about a device that stopped answering,
        and its recovery probe can prove the device is back between two polls of
        this coordinator.
        """
        if self._device_id is None:
            return True
        return self.client.device_online(self._device_id)

    @property
    def expected_offline(self) -> bool:
        """Whether this device is expected to stop answering.

        A solar inverter shuts itself down when there is no sun and comes back when
        there is, which is a normal part of its day rather than a fault. Such a
        device still goes unavailable and is still probed; only the level its
        transitions are logged at differs, so a night of silence is not a warning
        to wake someone up for.
        """
        return bool(
            self._subentry_data.get(
                OPTIONS_EXPECTED_OFFLINE, OPTIONS_DEFAULT_EXPECTED_OFFLINE
            )
        )

    def _device_policy(self, whole_device: bool) -> DevicePolicy:
        """How this device is polled while it is not answering.

        The probe entity is named only for a whole-device poll. A read of one entity
        on its own timer neither probes nor brings the device back: one register on
        its own says nothing about the rest of the device, and the refresh is what
        finds it.
        """
        return DevicePolicy(
            whole_device=whole_device,
            probe_key=self._probe_key if whole_device else None,
            expected_offline=self.expected_offline,
        )

    @property
    def _probe_key(self) -> str | None:
        """The entity a recovery probe reads, if the device names one.

        From the device's own configuration, so a device whose first entity is an
        expensive read - or one that a device answers slowly while it is waking up -
        can nominate a cheap one instead.
        """
        if self._device_info is None:
            return None
        return self._device_info.probe_key

    @callback
    def async_schedule_initial_poll(self) -> None:
        """Read the device once, after Home Assistant has finished starting.

        A read of a device that is not answering takes a timeout sequence, and
        Home Assistant waits for the work a setup starts. That is why this does
        not happen while the entry is being set up: entities are registered by
        then, so the whole device can be read once - rather than one entity at a
        time, which is what held startup up - and the read can wait until startup
        is over.
        """
        if self._initial_poll_scheduled:
            return
        self._initial_poll_scheduled = True
        if self.hass.state is CoreState.running:
            # Set up, or reloaded, while Home Assistant is already up: there is
            # no startup left to stay out of.
            self._async_launch_initial_poll()
            return
        _LOGGER.debug(
            "Deferring the first poll of %s until Home Assistant has started", self.name
        )
        self._unsubscribe_start = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, self._async_launch_initial_poll
        )

    @callback
    def _async_launch_initial_poll(self, _event: Event | None = None) -> None:
        """Run the deferred first poll as a task Home Assistant does not wait for."""
        self._unsubscribe_start = None
        if self._initial_poll_task is not None:
            return
        self._initial_poll_task = self.hass.async_create_background_task(
            self._async_initial_poll(),
            f"Modbus initial poll {self.name}",
            # This is called from `async_schedule_initial_poll()`, which runs
            # during setup. Starting the task on the next pass of the event loop
            # keeps a read out of the caller's stack entirely.
            eager_start=False,
        )

    @callback
    def async_cancel_initial_poll(self) -> None:
        """Drop the pending first poll, so an unloaded entry leaves nothing behind."""
        if self._unsubscribe_start is not None:
            self._unsubscribe_start()
            self._unsubscribe_start = None
        if self._initial_poll_task is not None:
            self._initial_poll_task.cancel()
            self._initial_poll_task = None
        self._initial_poll_scheduled = False

    async def _async_initial_poll(self) -> None:
        """Read every entity of the device once."""
        _LOGGER.debug("Reading %s for the first time", self.name)
        self._poll_all_entities = True
        await self.async_refresh()

    async def async_update(self) -> dict[str, Any]:
        """Fetch updated data for all registered entities.

        One poll per device at a time: a refresh that arrives while one is running
        is answered from it. That refresh is already asking for data newer than it
        was asked for, so the interval after it picks up anything that changes in
        between, and a slow device cannot be made slower by piling refreshes on it.
        """
        if self._poll_lock.locked():
            _LOGGER.debug(
                "Poll of %s already running, skipping this refresh", self.name
            )
            return self.data or {}
        async with self._poll_lock:
            try:
                if self._poll_all_entities:
                    self._poll_all_entities = False
                    return await self._update_device(entities=self._all_contexts())
                entities = [
                    ctx
                    for ctx in self._all_contexts()
                    if ctx.desc.scan_interval is None
                ]
                if not self.device_online:
                    # A device that is not answering is asked by this refresh and
                    # by nothing else: the entities that poll on their own timers
                    # do not read while it is away. So this refresh covers the
                    # whole device, because otherwise a device whose entities all
                    # have their own scan_interval would have nothing to ask it
                    # with and could never be found to be back. What it costs is
                    # one read of it when a probe is due, and nothing at all when
                    # one is not.
                    entities = self._all_contexts()
                elif not entities:
                    # Every entity has its own scan_interval and polls on its own
                    # timer, so there is nothing for the shared refresh to fetch.
                    _LOGGER.debug("No entities to refresh for %s", self.name)
                    return self.data or {}
                return await self._update_device(entities=entities)
            finally:
                self._initial_poll_done = True

    def _all_contexts(self) -> list[ModbusContext]:
        """Every registered entity of this device, in a stable order."""
        return sorted(self.async_contexts(), key=lambda ctx: ctx.device_id)

    async def _update_device(
        self, entities: list[ModbusContext], whole_device: bool = True
    ) -> dict[str, Any]:
        """Update data for a list of entities.

        A device that is not answering is not a failure to raise: the client reports
        it once, as a change of state, backs off and probes, and the entities it did
        not answer for go unavailable. `UpdateFailed` is for a poll that was unsound
        for a reason the device cannot be blamed for - a conversion that failed, or a
        poll that never finished - because that is what leaves the coordinator
        retrying.

        `whole_device` is False for a read of one entity on its own `scan_interval`.
        A register that times out then says nothing about the rest of the device, so
        such a read marks the device as answering when it comes back and otherwise
        only speaks for the entity it read.
        """
        _LOGGER.debug("Updating data for %s (%s)", self.name, self.client)
        if not entities:
            # A device config that no longer declares anything to read. There is
            # nothing to ask it and nothing to say about it.
            return {}
        if self._device_id is None:
            self._device_id = entities[0].device_id
        failed = False
        try:
            async with asyncio.timeout(_POLL_BACKSTOP):
                resp: dict[str, ModbusPDU] = await self.client.update_device(
                    entities,
                    max_read_size=self._max_read_size,
                    policy=self._device_policy(whole_device),
                )
        except ModbusNoResponseError as err:
            # The device went quiet part way through the cycle, and the client has
            # recorded it and put its next probe off. What was read before that is
            # still good data, and the rest of the cycle is no longer worth asking
            # for.
            _LOGGER.debug("%s stopped answering: %s", self.name, err)
            resp = err.partial
        except TimeoutError:
            _LOGGER.warning(
                "Reading %s did not finish within %s seconds",
                self.name,
                _POLL_BACKSTOP,
            )
            raise UpdateFailed(
                f"Reading {self.name} did not finish within {_POLL_BACKSTOP} seconds"
            ) from None
        data: dict[str, Any] = {}

        for entity in entities:
            if entity.desc.key not in resp:
                # This poll did not fetch it: the device stopped answering, or the
                # read came back unusable. There is no fresh value either way, and
                # the entity becomes unavailable rather than holding the last one.
                _LOGGER.debug(
                    "No value for key %s in this poll of %s",
                    entity.desc.key,
                    self.name,
                )
                self._unavailable_keys.add(entity.desc.key)
                continue
            modbus_response: ModbusPDU = resp[entity.desc.key]
            try:
                value: str | float | int | bool | datetime | None = self._convert_value(
                    entity.desc, modbus_response
                )
                data[entity.desc.key] = value
                self._unavailable_keys.discard(entity.desc.key)
                _LOGGER.debug("Value for key %s is %s", entity.desc.key, value)
            except ValueUnavailable as err:
                # Deliberately not added to `data`: the platforms' "is not None"
                # guard then skips the update, and availability comes from
                # ModbusCoordinatorEntity.available.
                _LOGGER.debug(
                    "%s is unavailable: %s (%s)",
                    entity.desc.key,
                    err.reason,
                    err.value,
                )
                self._unavailable_keys.add(entity.desc.key)
            except Exception:  # pylint: disable=broad-exception-caught
                failed = True
                _LOGGER.debug(
                    "Data not available for key: %s (%d)",
                    entity.desc.key,
                    entity.device_id,
                    exc_info=True,
                )

        if not data and failed:
            # Every entity this cycle read converted to nothing, and not because the
            # values were declared unavailable. That is a fault in the conversion
            # rather than a device that is off, so it is reported as a failure.
            raise UpdateFailed()
        return data

    def _convert_value(
        self, desc: ModbusEntityDescription, response: ModbusPDU
    ) -> str | float | int | bool | datetime | None:
        """Convert one entity's registers into the value it publishes.

        A composite entity assembles its fields itself; every other entity hands
        the response to the register conversion layer unchanged.
        """
        conversion: Conversion = Conversion(type(self.client))
        if isinstance(desc, ModbusCompositeEntityDescription):
            return CompositeConversion.from_registers(desc, response, conversion)
        return conversion.convert_from_response(desc=desc, response=response)

    async def async_update_entity(self, ctx: ModbusContext) -> None:
        """Update cached data for a specific entity.

        A device that has stopped answering is left to the refresh of the whole
        device: its entities have nothing to ask it with, and a read per entity
        while it is off is one read per entity per timer for as long as it is off.
        The entity stays unavailable until that refresh finds the device back.
        """
        if not self.device_online:
            _LOGGER.debug(
                "%s is not answering, leaving %s to the refresh of the device",
                self.name,
                ctx.desc.key,
            )
            return
        try:
            data = await self._update_device(entities=[ctx], whole_device=False)
        except UpdateFailed:
            return None
        if data:
            if self.data is None:
                self.data = {}
            self.data[ctx.desc.key] = data[ctx.desc.key]
            # The device answered this entity, so it is not down - even if the
            # shared poll that last failed said otherwise. Availability of the
            # other entities comes from the keys that poll did not reach, not
            # from this flag. `async_set_updated_data` would also do this, at
            # the cost of restarting the shared refresh timer on every read of
            # an entity that polls on its own.
            self.last_update_success = True

    def is_unavailable(self, ctx: ModbusContext) -> bool:
        """Whether this entity's last read was a declared non-value."""
        return ctx.desc.key in self._unavailable_keys

    def get_data(self, ctx: ModbusContext) -> str | int | float | bool | None:
        """Retrieve cached data for a specific entity"""
        if self.data and ctx.desc.key in self.data:
            return cast(str | int | float | bool | None, self.data[ctx.desc.key])
        return None
