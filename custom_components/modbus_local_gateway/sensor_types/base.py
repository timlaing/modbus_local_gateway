"""Sensor Entity Description for the Modbus local gateway integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntityDescription


@dataclass
class ModbusRequiredKeysMixin:
    """Mixin for required keys."""

    register_address: int


@dataclass
class ModbusSensorEntityDescription(
    SensorEntityDescription, ModbusRequiredKeysMixin
):
    """Describes Modbus sensor entity."""

    precision: int | None = None
    currency: bool = False
    previous_value_drop_threshold: float | None = None
    never_resets: bool = False
    register_count: int | None = 1
    register_multiplier: float | None = 0.1
    register_map: dict[int, str] | None = None
    icon: str | None = None
    string: bool | None = False
    float: bool | None = False
    holding_register: bool | None = False
