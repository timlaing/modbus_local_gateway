"""Representation of Modbus Gateway"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from pymodbus.pdu.pdu import ModbusPDU

from .context import ModbusContext
from .conversion import Conversion
from .entity_management.base import ModbusEntityDescription
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)


class ModbusCoordinatorEntity(CoordinatorEntity):
    """Base class for Modbus entities"""

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
        self._attr_unique_id: str | None = f"{ctx.device_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo | None = device
        self.coordinator: ModbusCoordinator
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
        value: str | int | float | bool | None,
    ) -> None:
        """Write data to the Modbus device"""
        try:
            await self.coordinator.client.write_data(self.coordinator_context, value)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to write %s to %s: %s", value, self.coordinator_context, exc
            )
            raise UpdateFailed from exc

        await self._async_update_if_not_in_progress()

    async def _async_update_if_not_in_progress(self, _=None) -> None:
        """Update the entity state if not already in progress."""
        try:
            await self._async_update_write_state()
        except asyncio.TimeoutError:
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
    def entity_description(self) -> ModbusEntityDescription:
        """Return the entity description."""
        return self.coordinator_context.desc


class ModbusCoordinator(TimestampDataUpdateCoordinator):
    """Update coordinator for modbus entries"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        gateway_device: dr.DeviceEntry,
        client: AsyncModbusTcpClientGateway,
        gateway: str,
        update_interval: int = 30,
    ) -> None:
        """Initialise the coordinator"""
        self.client: AsyncModbusTcpClientGateway = client
        self._gateway: str = gateway
        self._max_read_size: int = 1
        self._gateway_device: dr.DeviceEntry = gateway_device

        super().__init__(
            hass,
            config_entry=config_entry,
            logger=_LOGGER,
            name=f"Modbus Coordinator - {self._gateway}",
            update_interval=timedelta(seconds=update_interval),
            update_method=self.async_update,  # type: ignore
            always_update=True,
        )

    @property
    def gateway_device(self) -> dr.DeviceEntry:
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

    async def async_update(self) -> dict[str, Any]:
        """Fetch updated data for all registered entities"""
        entities: list[ModbusContext] = sorted(
            self.async_contexts(), key=lambda x: x.device_id
        )
        entities = [ctx for ctx in entities if ctx.desc.scan_interval is None]
        data: dict[str, Any] = await self._update_device(entities=entities)
        if data:
            return data
        raise UpdateFailed()

    async def _update_device(self, entities: list[ModbusContext]) -> dict[str, Any]:
        """Update data for a list of entities"""
        _LOGGER.debug("Updating data for %s (%s)", self.name, self.client)
        resp: dict[str, ModbusPDU] = await self.client.update_device(
            entities, max_read_size=self._max_read_size
        )
        data: dict[str, Any] = {}
        conversion: Conversion = Conversion(type(self.client))

        for entity in entities:
            if entity.desc.key in resp:
                modbus_response: ModbusPDU = resp[entity.desc.key]
                try:
                    value: str | float | int | bool | None = (
                        conversion.convert_from_response(
                            desc=entity.desc, response=modbus_response
                        )
                    )
                    data[entity.desc.key] = value
                    _LOGGER.debug("Value for key %s is %s", entity.desc.key, value)
                except Exception:  # pylint: disable=broad-exception-caught
                    _LOGGER.debug(
                        "Data not available for key: %s (%d)",
                        entity.desc.key,
                        entity.device_id,
                        exc_info=True,
                    )

        return data

    async def async_update_entity(self, ctx: ModbusContext) -> None:
        """Update cached data for a specific entity."""
        data: dict[str, Any] = await self._update_device(entities=[ctx])
        if data:
            if self.data is None:
                self.data = {}
            self.data[ctx.desc.key] = data[ctx.desc.key]
        return None

    def get_data(self, ctx: ModbusContext) -> str | int | bool | None:
        """Retrieve cached data for a specific entity"""
        if self.data and ctx.desc.key in self.data:
            return self.data[ctx.desc.key]
        return None
