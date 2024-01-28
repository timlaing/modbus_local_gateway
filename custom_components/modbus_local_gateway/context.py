"""Representation of Modbus Gateway Context"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .sensor_types.base import ModbusSensorEntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass
class ModbusContext:
    """Context object for use with the coordinator"""

    slave_id: int
    desc: ModbusSensorEntityDescription
