"""Module for the ModbusDeviceInfo class"""

from __future__ import annotations

import logging
from os.path import join
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.loader import JSON_TYPE

from ..device_configs import CONFIG_DIR
from .base import (
    ModbusEntityDescription,
    ModbusNumberEntityDescription,
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
    ModbusTextEntityDescription,
    ModbusBinarySensorEntityDescription,
)
from .const import (
    DEVICE,
    MANUFACTURER,
    MODEL,
    MAX_READ,
    MAX_READ_DEFAULT,
    NAME,
    CONTROL_TYPE,
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    CONV_SUM_SCALE,
    CONV_SHIFT_BITS,
    CONV_BITS,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_FLAGS,
    CONV_MAP,
    IS_FLOAT,
    IS_STRING,
    PRECISION,
    NEVER_RESETS,
    DEVICE_CLASS,
    STATE_CLASS,
    DEFAULT_STATE_CLASS,
    UNIT,
    UOM,
    UOM_MAPPING,
    ControlType,
    ModbusDataType,
)

_LOGGER = logging.getLogger(__name__)

DESCRIPTION_TYPE = (
    ModbusNumberEntityDescription
    | ModbusSelectEntityDescription
    | ModbusSensorEntityDescription
    | ModbusSwitchEntityDescription
    | ModbusTextEntityDescription
    | ModbusBinarySensorEntityDescription
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
        # Default control types per data type
        self.default_control_type = {
            ModbusDataType.HOLDING_REGISTER: ControlType.SENSOR,
            ModbusDataType.INPUT_REGISTER: ControlType.SENSOR,
            ModbusDataType.COIL: ControlType.BINARY_SENSOR,
            ModbusDataType.DISCRETE_INPUT: ControlType.BINARY_SENSOR,
        }
        # Allowed control types per data type
        self.allowed_control_types = {
            ModbusDataType.HOLDING_REGISTER: [
                ControlType.SENSOR,
                ControlType.NUMBER,
                ControlType.SELECT,
                ControlType.TEXT,
                ControlType.SWITCH,
            ],
            ModbusDataType.INPUT_REGISTER: [ControlType.SENSOR],
            ModbusDataType.COIL: [ControlType.BINARY_SENSOR, ControlType.SWITCH],
            ModbusDataType.DISCRETE_INPUT: [ControlType.BINARY_SENSOR],
        }

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
    def entity_descriptions(self) -> tuple[DESCRIPTION_TYPE, ...]:
        """Get the entity descriptions for the device"""
        if not self._config or not isinstance(self._config, dict):
            raise DeviceConfigError()

        descriptions = []
        for section in (ModbusDataType.HOLDING_REGISTER, ModbusDataType.INPUT_REGISTER,
                        ModbusDataType.COIL, ModbusDataType.DISCRETE_INPUT):
            if isinstance(self._config.get(section), dict):
                for entity, entity_data in self._config[section].items():
                    if isinstance(entity_data, dict):
                        desc = self._create_description(entity, section, entity_data)
                        if desc:
                            descriptions.append(desc)
        return tuple(descriptions)

    def get_uom(self, data, control_type) -> dict[str, str | None]:
        """Get the unit_of_measurement and device class"""
        unit = data.get(UOM)
        state_class: str | None = DEFAULT_STATE_CLASS
        device_class: str | None = None

        if unit in UOM_MAPPING:
            device_class = UOM_MAPPING[unit].get(DEVICE_CLASS, device_class)
            state_class = UOM_MAPPING[unit].get(STATE_CLASS, DEFAULT_STATE_CLASS)
            unit = UOM_MAPPING[unit].get(UNIT, unit)

        device_class = data.get(DEVICE_CLASS, device_class)
        state_class = data.get(STATE_CLASS, state_class)

        # Add state_class for sensors only and not for strings
        if device_class is None or data.get(IS_STRING, False) or control_type != ControlType.SENSOR:
            state_class = None

        return {
            "native_unit_of_measurement": unit,
            "device_class": device_class,
            "state_class": state_class,
        }

    def _create_description(self, entity: str, data_type: ModbusDataType, _data: dict[str, Any]) -> DESCRIPTION_TYPE | None:
        """Create an entity description based on data type"""
        control_type = _data.get(CONTROL_TYPE, self.default_control_type[data_type])
        if control_type not in self.allowed_control_types.get(data_type, []):
            _LOGGER.warning("Invalid control_type %s for data_type %s", control_type, data_type)
            return None

        uom = self.get_uom(_data, control_type)

        # Start with all attributes from _data
        params = dict(_data)

        # Override or add required and computed fields
        params.update({
            "key": entity,
            "name": " ".join([self.manufacturer, _data.get(NAME, entity)]),
            "data_type": data_type,
            "control_type": control_type,
            "register_address": _data.get(REGISTER_ADDRESS),
            "register_count": _data.get(REGISTER_COUNT, 1),
            "conv_sum_scale": _data.get(CONV_SUM_SCALE),
            "conv_shift_bits": _data.get(CONV_SHIFT_BITS),
            "conv_bits": _data.get(CONV_BITS),
            "conv_multiplier": _data.get(CONV_MULTIPLIER, 1.0),
            "conv_offset": _data.get(CONV_OFFSET),
            "conv_map": _data.get(CONV_MAP),
            "conv_flags": _data.get(CONV_FLAGS),
            "is_float": _data.get(IS_FLOAT, False),
            "is_string": _data.get(IS_STRING, False),
            "never_resets": _data.get(NEVER_RESETS, False),
            "native_unit_of_measurement": uom["native_unit_of_measurement"],
            "device_class": uom["device_class"],
            "state_class": uom["state_class"],
        })

        # Handle entity_category directly from params
        if "entity_category" in params:
            try:
                params["entity_category"] = EntityCategory(params["entity_category"])
            except ValueError:
                _LOGGER.warning("Invalid entity_category %s for %s", params["entity_category"], entity)
                del params["entity_category"]  # Remove invalid category

        # Select description class and add control-specific parameters
        desc_cls = None
        if control_type == ControlType.SENSOR:
            desc_cls = ModbusSensorEntityDescription
            # Set precision based on conv_multiplier if applicable
            if params.get("precision") is None:
                if params.get("conv_map") is None and params.get("conv_flags") is None and params.get("is_string") is None:
                    multiplier = params.get("conv_multiplier")
                    if not multiplier or multiplier % 1 == 0:
                        params["precision"] = 0
                    elif multiplier > 0.0001:
                        params["precision"] = len(f"{multiplier:.8g}".split(".")[-1].rstrip("0")) if "." in f"{multiplier:.8g}" else 0
                    else:
                        params["precision"] = 4
        elif control_type == ControlType.BINARY_SENSOR:
            desc_cls = ModbusBinarySensorEntityDescription
        elif control_type == ControlType.SWITCH:
            desc_cls = ModbusSwitchEntityDescription
            switch_data = _data.get("switch", {})
            if not isinstance(switch_data, dict):
                _LOGGER.warning("Switch configuration for %s should be a dictionary", entity)
                return None
            params["on"] = switch_data.get("on", 1)
            params["off"] = switch_data.get("off", 0)
        elif control_type == ControlType.SELECT:
            desc_cls = ModbusSelectEntityDescription
            params["select_options"] = _data.get("options")
            if not params["select_options"]:
                _LOGGER.warning("Missing options for select")
                return None
        elif control_type == ControlType.NUMBER:
            desc_cls = ModbusNumberEntityDescription
            number_data = _data.get("number", {})
            if not isinstance(number_data, dict):
                _LOGGER.warning("Number configuration for %s should be a dictionary", entity)
                return None
            if "min" not in number_data or "max" not in number_data:
                _LOGGER.warning("Missing min or max for number in %s", entity)
                return None
            params["min"] = number_data["min"]
            params["max"] = number_data["max"]
            params["precision"] = _data.get(PRECISION)
        elif control_type == ControlType.TEXT:
            desc_cls = ModbusTextEntityDescription
        else:
            _LOGGER.warning("Unsupported control_type %s", control_type)
            return None

        if desc_cls:
            # Filter out None values and create the description
            desc = desc_cls(**{k: v for k, v in params.items() if v is not None})
            if desc.validate():
                return desc
        return None
