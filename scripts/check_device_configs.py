"""Lint device metadata against the installed Home Assistant version."""
# cspell:words varh

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import re
import sys
from typing import Any

from homeassistant.components import binary_sensor, switch
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number.const import DEVICE_CLASS_UNITS as NUMBER_UNITS
from homeassistant.components.sensor.const import (
    DEVICE_CLASS_STATE_CLASSES,
    DEVICE_CLASS_UNITS,
    SensorDeviceClass,
    SensorStateClass,
)
import yaml

from custom_components.modbus_local_gateway.entity_management.const import (
    DEFAULT_STATE_CLASS,
    DEVICE_CLASS,
    STATE_CLASS,
    UNIT,
    UOM_MAPPING,
    ControlType,
    ModbusDataType,
)

CONFIG_DIR = Path("custom_components/modbus_local_gateway/device_configs")
# Some supported HA releases expose these enums without typing re-exports.
CLASS_ENUMS: dict[str, type[StrEnum]] = {
    "sensor": SensorDeviceClass,
    "number": NumberDeviceClass,
    "binary_sensor": getattr(binary_sensor, "BinarySensorDeviceClass"),  # noqa: B009
    "switch": getattr(switch, "SwitchDeviceClass"),  # noqa: B009
}
# Only enforce classes where the unit identifies the quantity. Percentages and
# unitless status codes need device knowledge, so deliberately have no rule.
REQUIRED_CLASSES = {
    "°C": {"temperature", "temperature_delta"},
    "°F": {"temperature", "temperature_delta"},
    "K": {"temperature", "temperature_delta"},
    "V": {"voltage"},
    "mV": {"voltage"},
    "A": {"current"},
    "mA": {"current"},
    "μA": {"current"},
    "W": {"power"},
    "kW": {"power"},
    "VA": {"apparent_power"},
    "var": {"reactive_power"},
    "kWh": {"energy"},
    "varh": {"reactive_energy"},
    "kvarh": {"reactive_energy"},
    "Hz": {"frequency"},
    "kHz": {"frequency"},
    "s": {"duration"},
    "min": {"duration"},
    "h": {"duration"},
    "d": {"duration"},
    "m³/h": {"volume_flow_rate"},
}
POWER_FACTOR = re.compile(r"\bpower[\s_]*factor\b", re.IGNORECASE)


def validate_entity(key: str, data: dict[str, Any], default: str) -> list[str]:
    """Validate raw metadata, including values the loader could discard."""
    errors: list[str] = []
    control = data.get("control", default)
    if not isinstance(control, str) or control not in set(ControlType):
        return [f"invalid control {control!r}"]
    unit = data.get("unit_of_measurement")
    if unit is not None and not isinstance(unit, str):
        return ["unit_of_measurement must be a string or null"]
    mapping = next((value for key, value in UOM_MAPPING.items() if key == unit), {})
    unit = mapping.get(UNIT, unit)
    device_class = data.get(DEVICE_CLASS, mapping.get(DEVICE_CLASS))
    state_class = data.get(STATE_CLASS)
    if state_class is not None and (
        not isinstance(state_class, str) or state_class not in set(SensorStateClass)
    ):
        return [f"invalid state_class {state_class!r}"]
    if control != "sensor" and state_class is not None:
        errors.append("state_class is only supported for sensors")
    if device_class is not None:
        enum = CLASS_ENUMS.get(control)
        if (
            enum is None
            or not isinstance(device_class, str)
            or device_class not in set(enum)
        ):
            errors.append(f"invalid device_class {device_class!r} for {control}")
            return errors
    if control not in ("sensor", "number"):
        return errors
    return errors + _validate_measurement(
        key,
        data,
        control,
        unit,
        device_class,
        mapping.get(STATE_CLASS, DEFAULT_STATE_CLASS),
    )


def _validate_measurement(
    key: str,
    data: dict[str, Any],
    control: str,
    unit: str | None,
    device_class: str | None,
    default_state: str,
) -> list[str]:
    """Check numeric units, required classes, and effective sensor statistics."""
    errors: list[str] = []
    state_class = data.get(STATE_CLASS)
    if data.get("string", False):
        if device_class is not None or state_class is not None:
            errors.append("string values cannot declare numeric classes or statistics")
        return errors
    aliases = {"kVArh": "kvarh", "uA": "μA", "minutes": "min", "Tag/e": "d"}
    if unit in aliases:
        errors.append(f"use unit {aliases[unit]!r} instead of {unit!r}")
    required = REQUIRED_CLASSES.get(unit or "", set())
    if POWER_FACTOR.search(f"{key} {data.get('name', '')}"):
        required = {"power_factor"}
    if required and device_class not in required:
        errors.append(
            f"expected device_class in {sorted(required)}, got {device_class!r}"
        )
    if device_class is None:
        return errors
    units = (
        DEVICE_CLASS_UNITS.get(SensorDeviceClass(device_class), {None})
        if control == "sensor"
        else NUMBER_UNITS.get(NumberDeviceClass(device_class), {None})
    )
    if unit not in units:
        errors.append(f"unit {unit!r} is invalid for {control} class {device_class!r}")
    if control == "sensor":
        effective_state = data.get(STATE_CLASS, default_state)
        if (
            effective_state is not None
            and effective_state
            not in DEVICE_CLASS_STATE_CLASSES.get(
                SensorDeviceClass(device_class), set()
            )
        ):
            errors.append(
                f"state_class {effective_state!r} is invalid for {device_class!r}"
            )
    return errors


def validate_file(path: Path) -> list[str]:
    """Return all metadata diagnostics for one YAML device config."""
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as err:
        return [f"{path}: {err}"]
    if not isinstance(config, dict):
        return [f"{path}: device config must be a mapping"]
    errors: list[str] = []
    for section in ModbusDataType:
        entries = config.get(section)
        if entries is None:
            continue
        if not isinstance(entries, dict):
            errors.append(f"{path}: {section}: expected a mapping")
            continue
        default = "sensor" if "word" in section else "binary_sensor"
        for key, data in entries.items():
            if not isinstance(data, dict):
                errors.append(f"{path}: {section}.{key}: expected a mapping")
                continue
            errors.extend(
                f"{path}: {section}.{key}: {message}"
                for message in validate_entity(str(key), data, default)
            )
    return errors


def main(paths: list[str] | None = None) -> int:
    """Check selected files, or every shipped config when no paths are passed."""
    files = (
        [Path(path) for path in paths] if paths else sorted(CONFIG_DIR.glob("*.yaml"))
    )
    if not files:
        print(f"No device configs found in {CONFIG_DIR}", file=sys.stderr)
        return 1
    errors = [error for path in files for error in validate_file(path)]
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"Validated {len(files)} device configs against Home Assistant metadata")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
