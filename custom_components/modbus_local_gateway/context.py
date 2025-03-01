"""Representation of Modbus Gateway Context"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .entity_management.base import ModbusEntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass
class ModbusContext:
    """Context object for use with the coordinator"""

    slave_id: int
    desc: ModbusEntityDescription
