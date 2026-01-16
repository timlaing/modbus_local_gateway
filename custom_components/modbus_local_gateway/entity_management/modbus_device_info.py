"""Module for the ModbusDeviceInfo class"""

from __future__ import annotations

import logging
from os.path import join
from typing import Any

from homeassistant.components.number import NumberMode
from homeassistant.const import CONF_SCAN_INTERVAL, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.loader import JSON_TYPE

from ..device_configs import CONFIG_DIR
from .base import (
    ModbusBinarySensorEntityDescription,
    ModbusNumberEntityDescription,
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
    ModbusTextEntityDescription,
)
from .const import (
    CONTROL_TYPE,
    CONV_BITS,
    CONV_FLAGS,
    CONV_MAP,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_SHIFT_BITS,
    CONV_SUM_SCALE,
    CONV_SWAP,
    DEFAULT_STATE_CLASS,
    DEVICE,
    DEVICE_CLASS,
    IS_FLOAT,
    IS_SIGNED,
    IS_STRING,
    MANUFACTURER,
    MAX_CHANGE,
    MAX_READ,
    MAX_READ_DEFAULT,
    MODEL,
    NAME,
    NEVER_RESETS,
    PRECISION,
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    STATE_CLASS,
    UNIT,
    UOM,
    UOM_MAPPING,
    ControlType,
    ModbusDataType,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

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
                ControlType.BINARY_SENSOR,
            ],
            ModbusDataType.INPUT_REGISTER: [
                ControlType.SENSOR,
                ControlType.BINARY_SENSOR,
            ],
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
        for section in (
            ModbusDataType.HOLDING_REGISTER,
            ModbusDataType.INPUT_REGISTER,
            ModbusDataType.COIL,
            ModbusDataType.DISCRETE_INPUT,
        ):
            if isinstance(self._config.get(section), dict):
                for entity, entity_data in self._config[section].items():
                    if isinstance(entity_data, dict) and (
                        desc := self._create_description(entity, section, entity_data)
                    ):
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
        if (
            device_class is None
            or data.get(IS_STRING, False)
            or control_type != ControlType.SENSOR
        ):
            state_class = None

        return {
            "native_unit_of_measurement": unit,
            "device_class": device_class,
            "state_class": state_class,
        }

    def _create_description(
        self, entity: str, data_type: ModbusDataType, _data: dict[str, Any]
    ) -> DESCRIPTION_TYPE | None:
        """Create an entity description based on data type"""
        control_type: ControlType = _data.get(
            CONTROL_TYPE, self.default_control_type[data_type]
        )
        if control_type not in self.allowed_control_types.get(data_type, []):
            _LOGGER.warning(
                "Invalid control_type %s for data_type %s", control_type, data_type
            )
            return None

        uom: dict[str, str | None] = self.get_uom(_data, control_type)
        params: dict[str, Any] = self._initialize_params(
            entity, _data, data_type, control_type, uom
        )

        if "entity_category" in params:
            self._handle_entity_category(params, entity)

        desc_cls: None | type[DESCRIPTION_TYPE] = self._select_description_class(
            control_type, params, _data, entity
        )
        if desc_cls:
            return self._create_description_instance(desc_cls, params)
        return None

    def _initialize_params(
        self,
        entity: str,
        _data: dict[str, Any],
        data_type: ModbusDataType,
        control_type: ControlType,
        uom: dict[str, str | None],
    ) -> dict[str, Any]:
        """Initialize parameters for the description"""
        params: dict[str, Any] = _data.copy()
        params.update(
            {
                "key": entity,
                "name": " ".join([self.manufacturer, _data.get(NAME, entity)]),
                "data_type": data_type,
                "control_type": control_type,
                "register_address": _data.get(REGISTER_ADDRESS),
                "register_count": _data.get(REGISTER_COUNT, 1),
                "conv_bits": _data.get(CONV_BITS),
                "conv_flags": _data.get(CONV_FLAGS),
                "conv_map": _data.get(CONV_MAP),
                "conv_multiplier": _data.get(CONV_MULTIPLIER),
                "conv_offset": _data.get(CONV_OFFSET),
                "conv_shift_bits": _data.get(CONV_SHIFT_BITS),
                "conv_sum_scale": _data.get(CONV_SUM_SCALE),
                "conv_swap": _data.get(CONV_SWAP),
                "is_float": _data.get(IS_FLOAT, False),
                "is_string": _data.get(IS_STRING, False),
                "is_signed": _data.get(IS_SIGNED, False),
                "never_resets": _data.get(NEVER_RESETS, False),
                "native_unit_of_measurement": uom["native_unit_of_measurement"],
                "device_class": uom["device_class"],
                "state_class": uom["state_class"],
                "max_change": _data.get(MAX_CHANGE),
                "scan_interval": _data.get(CONF_SCAN_INTERVAL),
            }
        )
        return params

    def _handle_entity_category(self, params, entity) -> None:
        """Handle entity category in parameters"""
        try:
            params["entity_category"] = EntityCategory(params["entity_category"])
        except ValueError:
            _LOGGER.warning(
                "Invalid entity_category %s for %s",
                params["entity_category"],
                entity,
            )
            del params["entity_category"]

    def _select_description_class(
        self, control_type, params, _data, entity
    ) -> None | type[DESCRIPTION_TYPE]:
        """Select the appropriate description class based on control type"""
        if params["data_type"] in [ModbusDataType.COIL, ModbusDataType.DISCRETE_INPUT]:
            if _data.get(CONV_BITS):
                _LOGGER.warning(
                    "bits cannot be set for %s or %s",
                    ModbusDataType.COIL,
                    ModbusDataType.DISCRETE_INPUT,
                )
                return None
            if _data.get(CONV_SHIFT_BITS):
                _LOGGER.warning(
                    "shift bits cannot be set for %s or %s",
                    ModbusDataType.COIL,
                    ModbusDataType.DISCRETE_INPUT,
                )
                return None

        if control_type == ControlType.SENSOR:
            return self._handle_sensor_description(params)
        elif control_type == ControlType.BINARY_SENSOR:
            return self._handle_binary_sensor_description(params, _data)
        elif control_type == ControlType.SWITCH:
            return self._handle_switch_description(params, _data, entity)
        elif control_type == ControlType.SELECT:
            return self._handle_select_description(params, _data)
        elif control_type == ControlType.NUMBER:
            return self._handle_number_description(params, _data, entity)
        elif control_type == ControlType.TEXT:
            return ModbusTextEntityDescription
        else:
            _LOGGER.warning("Unsupported control_type %s", control_type)
            return None

    def _handle_sensor_description(self, params) -> type[ModbusSensorEntityDescription]:
        """Handle sensor description specific logic"""
        if (
            params.get("precision") is None
            and params.get("conv_map") is None
            and params.get("conv_flags") is None
            and params.get("is_string") is None
        ):
            multiplier = params.get("conv_multiplier")
            if not multiplier or multiplier % 1 == 0:
                params["precision"] = 0
            elif multiplier > 0.0001:
                params["precision"] = (
                    len(f"{multiplier:.8g}".split(".")[-1].rstrip("0"))
                    if "." in f"{multiplier:.8g}"
                    else 0
                )
            else:
                params["precision"] = 4

        if (
            params.get("precision") is not None
            and params.get("conv_map") is None
            and params.get("conv_flags") is None
        ):
            params["suggested_display_precision"] = params["precision"]

        return ModbusSensorEntityDescription

    def _handle_binary_sensor_description(
        self, params, _data
    ) -> None | type[ModbusBinarySensorEntityDescription]:
        """Handle binary sensor description specific logic"""
        params["on"] = _data.get("on", True)
        params["off"] = _data.get("off", False)
        return ModbusBinarySensorEntityDescription

    def _handle_switch_description(
        self, params, _data, entity
    ) -> None | type[ModbusSwitchEntityDescription]:
        """Handle switch description specific logic"""
        switch_data = _data.get("switch", {})
        if _data.get(CONV_BITS) or _data.get(CONV_SHIFT_BITS):
            _LOGGER.warning("bits / shift bits cannot be set for Switches")
            return None

        if not isinstance(switch_data, dict):
            _LOGGER.warning(
                "Switch configuration for %s should be a dictionary", entity
            )
            return None
        params["on"] = switch_data.get("on", True)
        params["off"] = switch_data.get("off", False)
        return ModbusSwitchEntityDescription

    def _handle_select_description(
        self, params, _data
    ) -> None | type[ModbusSelectEntityDescription]:
        """Handle select description specific logic"""
        params["select_options"] = _data.get("options")
        if not params["select_options"]:
            _LOGGER.warning("Missing options for select")
            return None
        return ModbusSelectEntityDescription

    def _handle_number_description(
        self, params, _data, entity
    ) -> None | type[ModbusNumberEntityDescription]:
        """Handle number description specific logic"""
        number_data = _data.get("number", {})
        if not isinstance(number_data, dict):
            _LOGGER.warning(
                "Number configuration for %s should be a dictionary", entity
            )
            return None
        if "min" not in number_data or "max" not in number_data:
            _LOGGER.warning("Missing min or max for number in %s", entity)
            return None
        params["min"] = number_data["min"]
        params["max"] = number_data["max"]
        if "step" in number_data:
            params["native_step"] = number_data["step"]
        mode = number_data.get("mode")
        if mode is not None:
            if str(mode).lower() == "slider":
                params["mode"] = NumberMode.SLIDER
            elif str(mode).lower() == "box":
                params["mode"] = NumberMode.BOX
            else:
                _LOGGER.warning("Unknown number mode '%s' for %s", mode, entity)
        params["precision"] = _data.get(PRECISION)
        return ModbusNumberEntityDescription

    def _create_description_instance(
        self, desc_cls: type[DESCRIPTION_TYPE], params
    ) -> DESCRIPTION_TYPE | None:
        """Create an instance of the description class"""
        try:
            desc: DESCRIPTION_TYPE = desc_cls(
                **{k: v for k, v in params.items() if v is not None}
            )
            if desc.validate():
                return desc
        except TypeError as err:
            _LOGGER.warning(
                "Failed to create description instance for %s: %s", desc_cls, err
            )
        return None
