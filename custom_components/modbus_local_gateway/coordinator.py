"""Representation of Modbus Gateway"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
import logging
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
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
    CONF_LEGACY_ENTITY_IDS,
    CONF_LEGACY_ENTITY_IDS_DEFAULT,
    CONF_PREFIX,
    OPTIONS_DEFAULT_WRITE_FUNCTION,
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
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)

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

    async def _read_data(self) -> None:
        """Update the entity state."""
        await asyncio.wait_for(self._update_lock.acquire(), 0.1)
        try:
            await self.coordinator.async_update_entity(self.coordinator_context)
        finally:
            self._update_lock.release()

    async def _async_update_write_state(self) -> None:
        """Update the entity state and write it to the state machine."""
        await self._read_data()
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

        await self._async_update_if_not_in_progress()

    async def _async_update_if_not_in_progress(self, _: datetime | None = None) -> None:
        """Update the entity state if not already in progress."""
        try:
            await self._async_update_write_state()
        except TimeoutError:
            _LOGGER.debug("Update for entity %s is already in progress", self.name)

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
        """Remote start entity."""
        self._async_cancel_update_polling()
        self._async_schedule_future_update(0.1)
        if (
            self.coordinator_context.desc.scan_interval
            and self.coordinator_context.desc.scan_interval > 0
        ):
            self._cancel_timer = async_track_time_interval(
                self.hass,
                self._async_update_if_not_in_progress,
                timedelta(seconds=self.coordinator_context.desc.scan_interval),
            )
        self._attr_available = True
        self.async_write_ha_state()

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
        """Unavailable while the device is reporting a non-value for this entity."""
        if not super().available:
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
        # Settings of the device this coordinator polls, from its sub-entry.
        self._subentry_data: Mapping[str, Any] = dict(subentry.data) if subentry else {}
        # Definition of the device this coordinator polls, from its YAML file.
        self._device_info: ModbusDeviceInfo | None = device_info

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

    async def async_update(self) -> dict[str, Any]:
        """Fetch updated data for all registered entities"""
        entities: list[ModbusContext] = sorted(
            self.async_contexts(), key=lambda x: x.device_id
        )
        entities = [ctx for ctx in entities if ctx.desc.scan_interval is None]
        if not entities:
            # Every entity has its own scan_interval and polls on its own timer,
            # so there is nothing for the shared refresh to fetch.
            _LOGGER.debug("No entities to refresh for %s", self.name)
            return self.data or {}
        return await self._update_device(entities=entities)

    async def _update_device(self, entities: list[ModbusContext]) -> dict[str, Any]:
        """Update data for a list of entities.

        Raises `UpdateFailed` when the poll was unsound - the device did not
        reply, or a conversion failed unexpectedly and left nothing usable.
        """
        _LOGGER.debug("Updating data for %s (%s)", self.name, self.client)
        resp: dict[str, ModbusPDU] = await self.client.update_device(
            entities, max_read_size=self._max_read_size
        )
        data: dict[str, Any] = {}
        failed = False

        for entity in entities:
            if entity.desc.key in resp:
                modbus_response: ModbusPDU = resp[entity.desc.key]
                try:
                    value: str | float | int | bool | datetime | None = (
                        self._convert_value(entity.desc, modbus_response)
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

        if not data and (not resp or failed):
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
        """Update cached data for a specific entity."""
        try:
            data = await self._update_device(entities=[ctx])
        except UpdateFailed:
            return None
        if data:
            if self.data is None:
                self.data = {}
            self.data[ctx.desc.key] = data[ctx.desc.key]

    def is_unavailable(self, ctx: ModbusContext) -> bool:
        """Whether this entity's last read was a declared non-value."""
        return ctx.desc.key in self._unavailable_keys

    def get_data(self, ctx: ModbusContext) -> str | int | float | bool | None:
        """Retrieve cached data for a specific entity"""
        if self.data and ctx.desc.key in self.data:
            return cast(str | int | float | bool | None, self.data[ctx.desc.key])
        return None
