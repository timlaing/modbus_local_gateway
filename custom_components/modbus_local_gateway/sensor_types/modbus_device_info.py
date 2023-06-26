"""Module for the ModbusDeviceInfo class"""
from __future__ import annotations

from typing import Any
import logging
from os.path import join

from homeassistant.util.yaml import load_yaml

from ..devices import CONFIG_DIR
from .base import ModbusSensorEntityDescription
from .const import (
    DEVICE,
    MANUFACTURER,
    MODEL,
    MAX_READ_DEFAULT,
    MAX_READ,
    DEVICE_CLASS,
    UNIT,
    STATE_CLASS,
    UOM_MAPPING,
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    REGISTER_MAP,
    IS_FLOAT,
    IS_STRING,
    PRECISION,
    TITLE,
    ENTITIES,
    REGISTER_MULTIPLIER,
    UOM,
    DEFAULT_STATE_CLASS,
    ICON,
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
            "state_class": state_class}

    @property
    def entity_desciptions(self) -> tuple[ModbusSensorEntityDescription, ...]:
        """Get the entity descriptions for the device"""
        descriptions: list[ModbusSensorEntityDescription] = []
        for entity in self._config[ENTITIES]:
            _data:dict[str, Any] = self._config[ENTITIES][entity]

            uom = self.get_uom(_data)

            desc = ModbusSensorEntityDescription(
                key=entity,
                name=_data.get(TITLE, entity),
                register_address=_data[REGISTER_ADDRESS],
                register_count=_data.get(REGISTER_COUNT, 1),
                register_multiplier=_data.get(REGISTER_MULTIPLIER, 1),
                register_map=_data.get(REGISTER_MAP),
                icon=_data.get(ICON),
                precision=_data.get(PRECISION),
                string=_data.get(IS_STRING, False),
                float=_data.get(IS_FLOAT, False),
                **uom
            )

            descriptions.append(desc)

        return tuple(descriptions)

    @property
    def properties(self) -> tuple[ModbusSensorEntityDescription, ...]:
        """Get device properties descriptions"""
        descriptions: list[ModbusSensorEntityDescription] = []
        for entity in self._config[DEVICE]:
            if isinstance(self._config[DEVICE][entity], dict):
                _data:dict[str, Any] = self._config[DEVICE][entity]

                uom = self.get_uom(_data)

                desc = ModbusSensorEntityDescription(
                        key=entity,
                        name=_data.get(TITLE, entity),
                        register_address=_data[REGISTER_ADDRESS],
                        register_count=_data.get(REGISTER_COUNT),
                        register_multiplier=_data.get(REGISTER_MULTIPLIER),
                        register_map=_data.get(REGISTER_MAP),
                        icon=_data.get(ICON),
                        precision=_data.get(PRECISION),
                        string=_data.get(IS_STRING, False),
                        holding_register=True,
                        float=_data.get(IS_FLOAT, False),
                        **uom
                    )

                descriptions.append(desc)

        return tuple(descriptions)