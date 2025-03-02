"""Representation of Modbus Gateway"""

from __future__ import annotations

import logging
from datetime import timedelta, datetime
from typing import Any, Dict, List, Tuple

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    TimestampDataUpdateCoordinator,
)
from pymodbus.pdu.pdu import ModbusPDU

from .context import ModbusContext
from .entity_management.base import ModbusEntityDescription
from .entity_management.const import ModbusDataType
from .conversion import Conversion
from .tcp_client import AsyncModbusTcpClientGateway

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Type alias for read plan: category -> list of (start_address, count)
ReadPlan = Dict[str, List[Tuple[int, int]]]

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
        if isinstance(ctx.desc, ModbusEntityDescription):
            self.entity_description = ctx.desc
        else:
            raise TypeError()
        self._attr_unique_id: str | None = f"{ctx.slave_id}-{ctx.desc.key}"
        self._attr_device_info: DeviceInfo | None = device

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.available


class ModbusCoordinator(TimestampDataUpdateCoordinator):
    """Update coordinator for modbus entries"""

    def __init__(
        self,
        hass: HomeAssistant,
        gateway_device: dr.DeviceEntry,
        client: AsyncModbusTcpClientGateway,
        gateway: str,
        update_interval: int = 30,
    ) -> None:
        """Initialise the coordinator"""
        self.client: AsyncModbusTcpClientGateway = client
        self._gateway: str = gateway
        self._max_read_size: int
        self._gateway_device: dr.DeviceEntry = gateway_device
        self.started: bool = hass.is_running
        self._last_successful_update: datetime | None = None
        # Persistent read plan and tracking for max_read_size changes
        self._read_plan: ReadPlan | None = None
        self._last_max_read_size: int | None = None

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Modbus Coordinator - {self._gateway}",
            update_interval=timedelta(seconds=update_interval),
            update_method=self.async_update,  # type: ignore
            always_update=False,
        )

        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._async_enable_sync)

    async def _async_enable_sync(self, _) -> None:
        """Allow sync of devices after startup"""
        self.started = True

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

    @property
    def available(self) -> bool:
        """Return True if the coordinator is available"""
        if self._last_successful_update is None:
            return False
        threshold = timedelta(seconds=self.update_interval.total_seconds() * 2)
        return (datetime.now() - self._last_successful_update) < threshold

    @max_read_size.setter
    def max_read_size(self, value: int) -> None:
        """Sets the max register read size"""
        self._max_read_size = value

    async def _async_refresh(
        self,
        log_failures: bool = False,
        raise_on_auth_failed: bool = False,
        scheduled: bool = False,
        raise_on_entry_error: bool = False,
    ) -> None:
        return await super()._async_refresh(
            log_failures, raise_on_auth_failed, scheduled, raise_on_entry_error
        )

    async def async_update(self) -> dict[str, Any] | None:
        """Fetch updated data for all registered entities"""
        if self.started:
            entities: list[ModbusContext] = self.async_contexts()  # No need to sort by slave_id
            # Compute read plan on first update or if max_read_size changes
            if self._read_plan is None or self._last_max_read_size != self._max_read_size:
                self._read_plan = self._compute_read_plan(entities)
                self._last_max_read_size = self._max_read_size
            data = await self._update_device(entities=entities)
            if data:
                self._last_successful_update = datetime.now()
            return data

    def _compute_read_plan(self, entities: list[ModbusContext]) -> ReadPlan:
        """Compute the read plan by grouping addresses into efficient requests"""
        read_plan: ReadPlan = {
            ModbusDataType.HOLDING_REGISTER: [],
            ModbusDataType.INPUT_REGISTER: [],
            ModbusDataType.COIL: [],
            ModbusDataType.DISCRETE_INPUT: [],
        }
        # Group entities by category
        entities_by_category: Dict[str, List[ModbusContext]] = {
            category: [] for category in read_plan.keys()
        }
        for entity in entities:
            category = entity.desc.data_type
            entities_by_category[category].append(entity)

        # For each category, merge address ranges
        for category, ents in entities_by_category.items():
            ranges = [(e.desc.register_address, e.desc.register_count) for e in ents]
            read_plan[category] = self._merge_ranges(ranges, self._max_read_size)
        return read_plan

    def _merge_ranges(self, ranges: List[Tuple[int, int]], max_size: int) -> List[Tuple[int, int]]:
        """Merge address ranges into minimal read requests respecting max_size"""
        if not ranges:
            return []
        # Split ranges exceeding max_size
        split_ranges = []
        for start, count in ranges:
            while count > max_size:
                split_ranges.append((start, max_size))
                start += max_size
                count -= max_size
            if count > 0:
                split_ranges.append((start, count))
        # Sort by start address
        sorted_ranges = sorted(split_ranges, key=lambda x: x[0])
        merged = []
        current_start, current_count = sorted_ranges[0]
        current_end = current_start + current_count - 1
        # Merge overlapping or adjacent ranges
        for start, count in sorted_ranges[1:]:
            end = start + count - 1
            if start <= current_end + 1 and (end - current_start + 1) <= max_size:
                current_end = max(current_end, end)
            else:
                merged.append((current_start, current_end - current_start + 1))
                current_start = start
                current_end = end
        merged.append((current_start, current_end - current_start + 1))
        return merged

    async def _update_device(self, entities: list[ModbusContext]) -> dict[str, Any]:
        """Update data using the precomputed read plan"""
        # Execute the read plan
        responses = await self.client.batch_read(
            read_plan=self._read_plan,
            slave=entities[0].slave_id,  # All entities share the same slave_id
            max_read_size=self._max_read_size,
        )
        data: dict[str, Any] = {}
        # Extract values for each entity from responses
        for entity in entities:
            category = entity.desc.data_type
            start = entity.desc.register_address
            count = entity.desc.register_count
            response_offset = self._find_response(responses, category, start)
            if response_offset:
                response, offset = response_offset
                # Slice the response and create a new PDU for conversion
                if category in [ModbusDataType.HOLDING_REGISTER, ModbusDataType.INPUT_REGISTER]:
                    registers = response.registers[offset : offset + count]
                    sliced_response = type(response)(registers=registers)
                elif category in [ModbusDataType.COIL, ModbusDataType.DISCRETE_INPUT]:
                    bits = response.bits[offset : offset + count]
                    sliced_response = type(response)(bits=bits)
                try:
                    value = Conversion(type(self.client)).convert_from_response(
                        desc=entity.desc, response=sliced_response
                    )
                    data[entity.desc.key] = value
                    _LOGGER.debug("Value for key %s is %s", entity.desc.key, value)
                except Exception as e:
                    _LOGGER.debug(
                        "Data conversion failed for key: %s (%d): %s",
                        entity.desc.key, entity.slave_id, str(e), exc_info=True
                    )
            else:
                _LOGGER.debug("No response for %s", entity.desc.key)
        return data

    def _find_response(self, responses: Dict[str, List[ModbusPDU]], category: str, address: int) -> Tuple[ModbusPDU, int] | None:
        """Find the response and offset for a given address"""
        for (start, count), response in zip(self._read_plan[category], responses[category]):
            if start <= address < start + count:
                return response, address - start
        return None

    def get_data(self, ctx: ModbusContext) -> str | int | bool | None:
        """Retrieve cached data for a specific entity"""
        if self.data and ctx.desc.key in self.data:
            return self.data[ctx.desc.key]
        return None
