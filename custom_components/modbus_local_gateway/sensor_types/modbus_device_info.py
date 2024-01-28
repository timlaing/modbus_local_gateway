"""Module for the ModbusDeviceInfo class"""

from __future__ import annotations

import logging
from os.path import join
from typing import Any

from homeassistant.util.yaml import load_yaml

from ..devices import CONFIG_DIR
from .base import ModbusSensorEntityDescription
from .const import (
    BITS,
    CATEGORY,
    DEFAULT_STATE_CLASS,
    DEVICE,
    DEVICE_CLASS,
    ENTITIES,
    FLAGS,
    ICON,
    IS_FLOAT,
    IS_STRING,
    MANUFACTURER,
    MAX_READ,
    MAX_READ_DEFAULT,
    MODEL,
    NEVER_RESETS,
    PRECISION,
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    REGISTER_MAP,
    REGISTER_MULTIPLIER,
    SHIFT,
    STATE_CLASS,
    TITLE,
    UNIT,
    UOM,
    UOM_MAPPING,
)

_LOGGER = logging.getLogger(__name__)


class ModbusDeviceInfo:
    """Representation of YAML device info"""

    def __init__(self, fname) -> None:
        """Initialise the device config"""
        self.fname = fname
        filename = join(CONFIG_DIR, fname)
        self._config = load_yaml(filename)
        if self.manufacturer and self.model:
            _LOGGER.debug("Loaded device config %s", fname)

    @property
    def manufacturer(self) -> str:
        """Manufacturer of the device"""
        return self._config[DEVICE][MANUFACTURER]

    @property
    def model(self) -> str:
        """Model of the device"""
        return self._config[DEVICE][MODEL]

    @property
    def max_read_size(self) -> int:
        """Maximum number of registers to read in a single request"""
        return self._config[DEVICE].get(MAX_READ, MAX_READ_DEFAULT)

    def get_uom(self, data) -> dict[str, str]:
        """Get the unit_of_measurement and device class"""
        unit = data.get(UOM)
        state_class = None
        device_class = None

        if unit in UOM_MAPPING:
            device_class = UOM_MAPPING[unit].get(DEVICE_CLASS, device_class)
            state_class = UOM_MAPPING[unit].get(STATE_CLASS, DEFAULT_STATE_CLASS)
            unit = UOM_MAPPING[unit].get(UNIT, unit)

        device_class = data.get(DEVICE_CLASS, device_class)
        state_class = data.get(STATE_CLASS, state_class)

        return {
            "native_unit_of_measurement": unit,
            "device_class": device_class,
            "state_class": state_class,
        }

    def _create_descriptions(
        self, config: dict[str, Any], holding=False
    ) -> tuple[ModbusSensorEntityDescription, ...]:
        """Create the entity descriptions for the device"""
        descriptions: list[ModbusSensorEntityDescription] = []
        for entity in config:
            if isinstance(config[entity], dict):
                _data: dict[str, Any] = config[entity]

                uom = self.get_uom(_data)

                params: dict[str, Any] = {
                    "key": entity,
                    "name": _data.get(TITLE, entity),
                    "register_address": _data.get(REGISTER_ADDRESS),
                    "register_count": _data.get(REGISTER_COUNT),
                    "register_multiplier": _data.get(REGISTER_MULTIPLIER),
                    "register_map": _data.get(REGISTER_MAP),
                    "icon": _data.get(ICON),
                    "precision": _data.get(PRECISION),
                    "string": _data.get(IS_STRING),
                    "float": _data.get(IS_FLOAT),
                    "bits": _data.get(BITS),
                    "bit_shift": _data.get(SHIFT),
                    "flags": _data.get(FLAGS),
                    "never_resets": _data.get(NEVER_RESETS, False),
                    "entity_category": _data.get(CATEGORY),
                    "holding_register": holding,
                    **uom,
                }

                try:
                    desc = ModbusSensorEntityDescription(
                        **{k: params[k] for k in params if params[k] is not None}
                    )
                except TypeError:
                    _LOGGER.error(
                        "Unable to create entry %s: missing required values",
                        entity,
                        exc_info=True,
                    )
                    continue

                if not desc.validate():
                    continue

                descriptions.append(desc)

        return tuple(descriptions)

    @property
    def entity_desciptions(self) -> tuple[ModbusSensorEntityDescription, ...]:
        """Get the entity descriptions for the device"""
        return self._create_descriptions(self._config[ENTITIES])

    @property
    def properties(self) -> tuple[ModbusSensorEntityDescription, ...]:
        """Get device properties descriptions"""
        return self._create_descriptions(self._config[DEVICE], holding=True)
