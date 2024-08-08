"""Module for the ModbusDeviceInfo class"""

from __future__ import annotations

import logging
from os.path import join
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.loader import JSON_TYPE

from ..devices import CONFIG_DIR
from .base import (
    ModbusEntityDescription,
    ModbusNumberEntityDescription,
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
    ModbusTextEntityDescription,
)
from .const import (
    BITS,
    CATEGORY,
    CONTROL_TYPE,
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
    OPTIONS,
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
    ControlType,
)

_LOGGER = logging.getLogger(__name__)

DESCRIPTION_TYPE = (
    ModbusNumberEntityDescription
    | ModbusSelectEntityDescription
    | ModbusSensorEntityDescription
    | ModbusSwitchEntityDescription
    | ModbusTextEntityDescription
)


class DeviceConfigError(HomeAssistantError):
    """Device Configuration Error"""


class ModbusDeviceInfo:
    """Representation of YAML device info"""

    def __init__(self, fname: str) -> None:
        """Initialise the device config"""
        self.fname: str = fname
        filename: str = join(CONFIG_DIR, fname)
        self._config: JSON_TYPE | None = load_yaml(filename)
        if self.manufacturer and self.model:
            _LOGGER.debug("Loaded device config %s", fname)

    @property
    def manufacturer(self) -> str:
        """Manufacturer of the device"""
        if (
            self._config
            and isinstance(self._config, dict)
            and DEVICE in self._config
            and isinstance(self._config[DEVICE], dict)
            and MANUFACTURER in self._config[DEVICE]
        ):
            return self._config[DEVICE][MANUFACTURER]
        raise DeviceConfigError()

    @property
    def model(self) -> str:
        """Model of the device"""
        if (
            self._config
            and isinstance(self._config, dict)
            and DEVICE in self._config
            and isinstance(self._config[DEVICE], dict)
            and MODEL in self._config[DEVICE]
        ):
            return self._config[DEVICE][MODEL]
        raise DeviceConfigError()

    @property
    def max_read_size(self) -> int:
        """Maximum number of registers to read in a single request"""
        if self._config and isinstance(self._config, dict) and DEVICE in self._config:
            return self._config[DEVICE].get(MAX_READ, MAX_READ_DEFAULT)
        raise DeviceConfigError()

    @property
    def entity_desciptions(self) -> tuple[DESCRIPTION_TYPE, ...]:
        """Get the entity descriptions for the device"""
        if self._config and isinstance(self._config, dict) and ENTITIES in self._config:
            return self._create_descriptions(self._config[ENTITIES])
        raise DeviceConfigError()

    @property
    def properties(self) -> tuple[ModbusEntityDescription, ...]:
        """Get device properties descriptions"""
        if self._config and isinstance(self._config, dict) and DEVICE in self._config:
            return self._create_descriptions(self._config[DEVICE], holding=True)
        raise DeviceConfigError()

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

    @classmethod
    def _get_description_class(
        cls, entity, params: dict, holding: bool, _data: dict
    ) -> None | ModbusEntityDescription:
        """Gets the class for the description"""
        try:
            desc_cls = ModbusSensorEntityDescription
            if holding:
                match (params["control_type"]):
                    case ControlType.SWITCH:
                        desc_cls = ModbusSwitchEntityDescription
                        if ControlType.SWITCH in _data and isinstance(
                            _data[ControlType.SWITCH], dict
                        ):
                            params.update(_data[ControlType.SWITCH])
                    case ControlType.SELECT:
                        desc_cls = ModbusSelectEntityDescription
                        params.update({"select_options": _data.get(OPTIONS)})
                    case ControlType.TEXT:
                        desc_cls = ModbusTextEntityDescription
                    case ControlType.NUMBER:
                        desc_cls = ModbusNumberEntityDescription
                        if ControlType.NUMBER in _data and isinstance(
                            _data[ControlType.NUMBER], dict
                        ):
                            params.update(_data[ControlType.NUMBER])
                            params.update({"precision": _data.get(PRECISION)})
            else:
                params.update({"suggested_display_precision": _data.get(PRECISION)})

            desc: DESCRIPTION_TYPE = desc_cls(
                **{k: params[k] for k in params if params[k] is not None}
            )

            return desc

        except TypeError:
            _LOGGER.error(
                "Unable to create entry %s: missing required values",
                entity,
                exc_info=True,
            )
            return

    def _create_descriptions(
        self, config: dict[str, Any], holding=False
    ) -> tuple[DESCRIPTION_TYPE, ...]:
        """Create the entity descriptions for the device"""
        descriptions: list[DESCRIPTION_TYPE] = []
        for entity in config:
            if isinstance(config[entity], dict):
                _data: dict[str, Any] = config[entity]

                uom: dict[str, str] = self.get_uom(_data)

                params: dict[str, Any] = {
                    "key": entity,
                    "name": _data.get(TITLE, entity),
                    "register_address": _data.get(REGISTER_ADDRESS),
                    "register_count": _data.get(REGISTER_COUNT),
                    "register_multiplier": _data.get(REGISTER_MULTIPLIER),
                    "register_map": _data.get(REGISTER_MAP),
                    "icon": _data.get(ICON),
                    "string": _data.get(IS_STRING),
                    "float": _data.get(IS_FLOAT),
                    "bits": _data.get(BITS),
                    "bit_shift": _data.get(SHIFT),
                    "flags": _data.get(FLAGS),
                    "never_resets": _data.get(NEVER_RESETS, False),
                    "holding_register": holding,
                    "control_type": _data.get(CONTROL_TYPE, ControlType.SENSOR),
                    **uom,
                }

                try:
                    params["entity_category"] = EntityCategory(_data.get(CATEGORY))
                except ValueError:
                    pass

                desc: None | ModbusEntityDescription = self._get_description_class(
                    entity, params, holding, _data
                )

                if not desc or not desc.validate():
                    continue

                descriptions.append(desc)

        return tuple(descriptions)
