"""Sensor Entity Description for the Modbus local gateway integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntityDescription

from .const import (
    BITS,
    IS_FLOAT,
    IS_STRING,
    PRECISION,
    REGISTER_COUNT,
    REGISTER_MULTIPLIER,
    SHIFT,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True, frozen=True)
class ModbusRequiredKeysMixin:
    """Mixin for required keys."""

    register_address: int


@dataclass(kw_only=True, frozen=True)
class ModbusSensorEntityDescription(SensorEntityDescription, ModbusRequiredKeysMixin):
    """Describes Modbus sensor entity."""

    precision: int | None = None
    currency: bool = False
    previous_value_drop_threshold: float | None = None
    never_resets: bool = False
    register_count: int | None = 1
    register_multiplier: float | None = 1.0
    register_map: dict[int, str] | None = None
    icon: str | None = None
    string: bool | None = False
    float: bool | None = False
    holding_register: bool | None = False
    flags: dict[int, str] | None = None
    bit_shift: int | None = None
    bits: int | None = None

    def validate(self) -> bool:
        """Validation the entity description"""
        valid = True
        if self.float and self.string:
            _LOGGER.warning(
                "Unable for create entity for %s, both string and float defined",
                self.key,
            )
            valid = False

        elif (
            self.bit_shift
            or self.bits
            or self.precision
            or self.register_multiplier != 1.0
        ) and self.string:
            _LOGGER.warning(
                "Unable for create entity for %s, %s, %s, %s and %s not valid for %s",
                self.key,
                BITS,
                SHIFT,
                PRECISION,
                REGISTER_MULTIPLIER,
                IS_STRING,
            )
            valid = False

        elif (
            self.bit_shift or self.bits or self.register_multiplier != 1.0
        ) and self.float:
            _LOGGER.warning(
                "Unable for create entity for %s, %s, %s and %s not valid for %s",
                self.key,
                BITS,
                SHIFT,
                REGISTER_MULTIPLIER,
                IS_FLOAT,
            )
            valid = False

        elif self.register_count != 2 and self.float:
            _LOGGER.warning(
                "Unable for create entity for %s, %s outside valid range not valid for %s",
                self.key,
                REGISTER_COUNT,
                IS_FLOAT,
            )
            valid = False

        return valid
