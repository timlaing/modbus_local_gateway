"""Module for the ModbusDeviceInfo class"""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
import logging
import math
from os.path import join
from typing import Any, cast

from homeassistant.components.number import NumberMode
from homeassistant.const import CONF_SCAN_INTERVAL, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml
from homeassistant.util.yaml.loader import JSON_TYPE

from ..device_configs import CONFIG_DIR
from .base import (
    ModbusBinarySensorEntityDescription,
    ModbusDateTimeEntityDescription,
    ModbusFieldDescription,
    ModbusNumberEntityDescription,
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
    ModbusTextEntityDescription,
)
from .const import (
    COMPOSITE,
    COMPOSITE_FIELDS,
    COMPOSITE_TYPE,
    CONTROL_TYPE,
    CONV_BITS,
    CONV_FLAGS,
    CONV_MAP,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_SHIFT_BITS,
    CONV_SUM_SCALE,
    CONV_SWAP,
    CONV_UNAVAILABLE_VALUES,
    CONV_WRITE_OFFSET,
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
    NO_FLAG_VALUE,
    PRECISION,
    PROBE_KEY,
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    STATE_CLASS,
    UNIT,
    UOM,
    UOM_MAPPING,
    WRITE_FUNCTION,
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

DESCRIPTION_TYPE = (
    ModbusNumberEntityDescription
    | ModbusSelectEntityDescription
    | ModbusSensorEntityDescription
    | ModbusSwitchEntityDescription
    | ModbusTextEntityDescription
    | ModbusBinarySensorEntityDescription
    | ModbusDateTimeEntityDescription
)

# The keys a `fields:` entry understands. Everything else is left out so a typo
# cannot be read as a conversion the field never had.
FIELD_KEYS: tuple[str, ...] = (
    REGISTER_ADDRESS,
    REGISTER_COUNT,
    CONV_SWAP,
    CONV_MULTIPLIER,
    CONV_OFFSET,
    CONV_WRITE_OFFSET,
    CONV_UNAVAILABLE_VALUES,
    CONV_BITS,
    CONV_SHIFT_BITS,
    IS_SIGNED,
    IS_FLOAT,
    IS_STRING,
)

# The keys a `composite:` entry takes next to its own `type`, `data_type` and
# `fields`: the entity-level options every other entity gets, so a composite
# polls and presents like the rest of the device instead of silently losing them.
ENTITY_KEYS: tuple[str, ...] = (
    CONF_SCAN_INTERVAL,
    "icon",
    "entity_category",
    "entity_registry_enabled_default",
    WRITE_FUNCTION,
)


def _optional_int(value: Any) -> int | None:
    """Return an optional integer key as an int, or None when it is absent.

    `bits` and `shift_bits` are read straight from YAML, so a quoted number or a
    word has to fail here rather than deep inside the geometry check.
    """
    return None if value is None else int(value)


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
            return cast(str, self._config[DEVICE][MANUFACTURER])
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
            return cast(str, self._config[DEVICE][MODEL])
        raise DeviceConfigError()

    @property
    def max_read_size(self) -> int:
        """Maximum number of registers to read in a single request"""
        if self._config and isinstance(self._config, dict) and DEVICE in self._config:
            return cast(int, self._config[DEVICE].get(MAX_READ, MAX_READ_DEFAULT))
        raise DeviceConfigError()

    @cached_property
    def probe_key(self) -> str | None:
        """The entity a recovery probe reads, when the device names one.

        A device that has stopped answering is asked one question to find out
        whether it is back, and the answer should come from an entity the device
        answers as long as it is powered at all: a status word rather than a
        history, a register rather than a set of them. Naming it here is how a
        device whose first entity is not that chooses; without a name the first
        entity of the poll is used, which is the right answer for most devices.

        A name that is not one of the device's own entities is a warning rather
        than a failure: the probe falls back to the first entity, which is what it
        would have done anyway.

        Decided once and kept, because every poll asks for it, and a name that is
        wrong in a device configuration is worth saying once rather than on every
        poll that goes on to probe the wrong entity.
        """
        device = self._config.get(DEVICE) if isinstance(self._config, dict) else None
        stored = device.get(PROBE_KEY) if isinstance(device, dict) else None
        if stored is None:
            return None
        if stored not in self._declared_keys():
            _LOGGER.warning(
                "%s: %s is %s, which is not an entity of this device, so its "
                "recovery probe reads the first entity instead",
                self.fname,
                PROBE_KEY,
                stored,
            )
            return None
        return str(stored)

    def _declared_keys(self) -> set[str]:
        """The entity names the config declares, without building any of them.

        Cheaper than `entity_descriptions`, and enough to tell whether the key
        named for a probe is one this device actually has.
        """
        config: Any = self._config
        declared: set[str] = set()
        if not isinstance(config, dict):
            return declared
        for section in (
            ModbusDataType.HOLDING_REGISTER,
            ModbusDataType.INPUT_REGISTER,
            ModbusDataType.COIL,
            ModbusDataType.DISCRETE_INPUT,
            COMPOSITE,
        ):
            section_data: Any = config.get(section)
            if isinstance(section_data, dict):
                declared |= {str(name) for name in section_data}
        return declared

    @property
    def entity_descriptions(self) -> tuple[DESCRIPTION_TYPE, ...]:
        """Get the entity descriptions for the device"""
        if not self._config or not isinstance(self._config, dict):
            raise DeviceConfigError()

        descriptions: list[DESCRIPTION_TYPE] = []
        for section in (
            ModbusDataType.HOLDING_REGISTER,
            ModbusDataType.INPUT_REGISTER,
            ModbusDataType.COIL,
            ModbusDataType.DISCRETE_INPUT,
        ):
            descriptions += [
                desc
                for desc in (
                    self._create_description(entity, section, entity_data)
                    for entity, entity_data in self._entities_of(section)
                )
                if desc
            ]
        descriptions += [
            desc
            for desc in (
                self._create_composite_description(entity, entity_data)
                for entity, entity_data in self._entities_of(COMPOSITE)
            )
            if desc
        ]
        return tuple(descriptions)

    def _entities_of(self, section: str) -> list[tuple[str, dict[str, Any]]]:
        """The entity definitions of one config section, ignoring unusable ones"""
        declared = self._config.get(section) if isinstance(self._config, dict) else None
        if not isinstance(declared, dict):
            return []
        return [
            (entity, entity_data)
            for entity, entity_data in declared.items()
            if isinstance(entity_data, dict)
        ]

    def _create_composite_description(
        self, entity: str, data: dict[str, Any]
    ) -> ModbusDateTimeEntityDescription | None:
        """Create a description for an entity assembled from several registers"""
        composite_type = self._composite_type(entity, data)
        if composite_type is None:
            return None

        data_type = self._composite_data_type(entity, data)
        if data_type is None:
            return None

        fields = self._composite_fields(entity, data, data_type)
        if fields is None:
            return None

        write_function = data.get(WRITE_FUNCTION)
        if write_function is not None:
            # A device that refuses preset multiple registers (FC 0x10) across
            # a span of adjacent registers can only have that span written
            # register by register, which is what `single` asks for. It is not
            # the entry-wide option: on such hardware the clock is the
            # exception and the settings registers around it still need the
            # block write.
            try:
                write_function = WriteFunction(write_function)
            except ValueError:
                _LOGGER.warning(
                    "Unable to create entity for %s: %s must be one of %s, got %s",
                    entity,
                    WRITE_FUNCTION,
                    ", ".join(WriteFunction),
                    data[WRITE_FUNCTION],
                )
                return None

        addresses: list[int] = [field.address for field in fields]
        params: dict[str, Any] = {
            key: data[key] for key in ENTITY_KEYS if data.get(key) is not None
        }
        if "entity_category" in params:
            self._handle_entity_category(params, entity)
        params.update({
            "key": entity,
            "name": "".join(["", data.get(NAME, entity)]),
            "data_type": data_type,
            "control_type": ControlType.DATETIME,
            "composite_type": composite_type,
            "fields": fields,
            # The span covers every field, so the entity reads as one value
            # and the gaps between non-adjacent fields are not addressed.
            "register_address": min(addresses),
            "register_count": max(field.end_address for field in fields)
            - min(addresses)
            + 1,
        })
        composite_desc: ModbusDateTimeEntityDescription | None = cast(
            "ModbusDateTimeEntityDescription | None",
            self._create_description_instance(
                ModbusDateTimeEntityDescription,
                params,
            ),
        )
        return composite_desc

    def _composite_type(
        self, entity: str, data: dict[str, Any]
    ) -> CompositeType | None:
        """Read the composite type, e.g. `type: datetime`"""
        stored: Any = data.get(COMPOSITE_TYPE)
        if not isinstance(stored, str):
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be one of %s, got %s",
                entity,
                COMPOSITE_TYPE,
                ", ".join(str(member) for member in CompositeType),
                stored,
            )
            return None
        try:
            return CompositeType(stored)
        except ValueError:
            _LOGGER.warning(
                "Unable to create entity for %s: %s must be one of %s, got %s",
                entity,
                COMPOSITE_TYPE,
                ", ".join(str(member) for member in CompositeType),
                stored,
            )
            return None

    def _composite_data_type(
        self, entity: str, data: dict[str, Any]
    ) -> ModbusDataType | None:
        """Read the Modbus data type the fields live in.

        Only registers can hold a composite: a coil is a single bit, and a
        discrete input cannot be written.
        """
        stored = data.get("data_type", ModbusDataType.HOLDING_REGISTER)
        if stored not in (
            ModbusDataType.HOLDING_REGISTER,
            ModbusDataType.INPUT_REGISTER,
        ):
            _LOGGER.warning(
                "Unable to create entity for %s: data_type must be %s or %s for a "
                "%s, got %s",
                entity,
                ModbusDataType.HOLDING_REGISTER,
                ModbusDataType.INPUT_REGISTER,
                COMPOSITE,
                stored,
            )
            return None
        return ModbusDataType(stored)

    def _composite_fields(
        self, entity: str, data: dict[str, Any], data_type: ModbusDataType
    ) -> tuple[ModbusFieldDescription, ...] | None:
        """Build the field descriptions of a composite entity"""
        declared = data.get(COMPOSITE_FIELDS)
        if not isinstance(declared, dict) or not declared:
            _LOGGER.warning(
                "Unable to create entity for %s: %s needs a %s mapping",
                entity,
                COMPOSITE,
                COMPOSITE_FIELDS,
            )
            return None

        fields: list[ModbusFieldDescription] = []
        for field_name, field_data in declared.items():
            field = self._composite_field(entity, field_name, field_data)
            if field is None or not field.validate(data_type):
                return None
            fields.append(field)
        return tuple(fields)

    def _composite_field(
        self, entity: str, field_name: Any, field_data: Any
    ) -> ModbusFieldDescription | None:
        """Build one field description, warning about anything unusable"""
        if not isinstance(field_data, dict):
            _LOGGER.warning(
                "Unable to create entity for %s: field %s should be a dictionary",
                entity,
                field_name,
            )
            return None
        if field_data.get(REGISTER_ADDRESS) is None:
            _LOGGER.warning(
                "Unable to create entity for %s: field %s is missing %s",
                entity,
                field_name,
                REGISTER_ADDRESS,
            )
            return None

        unsupported: list[str] = [
            key for key in (CONV_MAP, CONV_FLAGS) if field_data.get(key) is not None
        ]
        if unsupported:
            _LOGGER.warning(
                "Unable to create entity for %s: field %s cannot use %s - a "
                "date or time part has no set of values to map or flag",
                entity,
                field_name,
                ", ".join(unsupported),
            )
            return None

        unknown: list[str] = [key for key in field_data if key not in FIELD_KEYS]
        if unknown:
            _LOGGER.warning(
                "Unable to create entity for %s: field %s has unknown keys %s",
                entity,
                field_name,
                ", ".join(sorted(unknown)),
            )
            return None

        try:
            return ModbusFieldDescription(
                key=field_name,
                address=int(field_data[REGISTER_ADDRESS]),
                size=int(field_data.get(REGISTER_COUNT, 1)),
                conv_swap=field_data.get(CONV_SWAP),
                conv_multiplier=field_data.get(CONV_MULTIPLIER),
                conv_offset=field_data.get(CONV_OFFSET),
                conv_write_offset=_optional_int(field_data.get(CONV_WRITE_OFFSET)),
                conv_unavailable_values=field_data.get(CONV_UNAVAILABLE_VALUES),
                conv_bits=_optional_int(field_data.get(CONV_BITS)),
                conv_shift_bits=_optional_int(field_data.get(CONV_SHIFT_BITS)),
                is_signed=field_data.get(IS_SIGNED, False),
                is_float=field_data.get(IS_FLOAT, False),
                is_string=field_data.get(IS_STRING, False),
            )
        except (TypeError, ValueError) as err:
            _LOGGER.warning(
                "Unable to create entity for %s: field %s has a bad address, "
                "size, %s or %s: %s",
                entity,
                field_name,
                CONV_BITS,
                CONV_SHIFT_BITS,
                err,
            )
            return None

    def get_uom(
        self, data: dict[str, Any], control_type: ControlType
    ) -> dict[str, str | None]:
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
        params.update({
            "key": entity,
            "name": "".join(["", _data.get(NAME, entity)]),
            "data_type": data_type,
            "control_type": control_type,
            "register_address": _data.get(REGISTER_ADDRESS),
            "register_count": _data.get(REGISTER_COUNT, 1),
            "conv_bits": _data.get(CONV_BITS),
            "conv_flags": _data.get(CONV_FLAGS),
            "conv_no_flag_value": _data.get(NO_FLAG_VALUE),
            "conv_map": _data.get(CONV_MAP),
            "conv_unavailable_values": _data.get(CONV_UNAVAILABLE_VALUES),
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
        })
        return params

    def _handle_entity_category(self, params: dict[str, Any], entity: str) -> None:
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
        self,
        control_type: ControlType,
        params: dict[str, Any],
        _data: dict[str, Any],
        entity: str,
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

        handlers: dict[str, Callable[[], type[DESCRIPTION_TYPE] | None]] = {
            ControlType.SENSOR: lambda: self._handle_sensor_description(params),
            ControlType.BINARY_SENSOR: lambda: self._handle_binary_sensor_description(
                params, _data
            ),
            ControlType.SWITCH: lambda: self._handle_switch_description(
                params, _data, entity
            ),
            ControlType.SELECT: lambda: self._handle_select_description(params, _data),
            ControlType.NUMBER: lambda: self._handle_number_description(
                params, _data, entity
            ),
            ControlType.TEXT: lambda: ModbusTextEntityDescription,
        }
        handler: Callable[[], type[DESCRIPTION_TYPE] | None] | None = handlers.get(
            control_type
        )
        if handler is None:
            _LOGGER.warning("Unsupported control_type %s", control_type)
            return None
        return handler()

    def _handle_sensor_description(
        self, params: dict[str, Any]
    ) -> type[ModbusSensorEntityDescription]:
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
        self, params: dict[str, Any], _data: dict[str, Any]
    ) -> None | type[ModbusBinarySensorEntityDescription]:
        """Handle binary sensor description specific logic"""
        params["on"] = _data.get("on", True)
        params["off"] = _data.get("off", False)
        return ModbusBinarySensorEntityDescription

    def _handle_switch_description(
        self, params: dict[str, Any], _data: dict[str, Any], entity: str
    ) -> None | type[ModbusSwitchEntityDescription]:
        """Handle switch description specific logic"""
        switch_data = _data.get("switch", {})
        if not isinstance(switch_data, dict):
            _LOGGER.warning(
                "Switch configuration for %s should be a dictionary", entity
            )
            return None
        params["on"] = switch_data.get("on", True)
        params["off"] = switch_data.get("off", False)
        return ModbusSwitchEntityDescription

    def _handle_select_description(
        self, params: dict[str, Any], _data: dict[str, Any]
    ) -> None | type[ModbusSelectEntityDescription]:
        """Handle select description specific logic"""
        params["select_options"] = _data.get("options")
        if not params["select_options"]:
            _LOGGER.warning("Missing options for select")
            return None
        return ModbusSelectEntityDescription

    def _handle_number_description(
        self, params: dict[str, Any], _data: dict[str, Any], entity: str
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
            try:
                step = float(number_data["step"])
            except (OverflowError, TypeError, ValueError):  # fmt: skip
                _LOGGER.warning("Invalid step for number in %s", entity)
                return None
            if not math.isfinite(step) or step <= 0:
                _LOGGER.warning("Invalid step for number in %s", entity)
                return None
            params["native_step"] = step
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
        self, desc_cls: type[DESCRIPTION_TYPE], params: dict[str, Any]
    ) -> DESCRIPTION_TYPE | None:
        """Create an instance of the description class"""
        try:
            desc: DESCRIPTION_TYPE = desc_cls(**{
                k: v for k, v in params.items() if v is not None
            })
            if desc.validate():
                return desc
        except TypeError as err:
            _LOGGER.warning(
                "Failed to create description instance for %s: %s", desc_cls, err
            )
        return None
