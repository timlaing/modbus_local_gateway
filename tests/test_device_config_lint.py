"""Regression coverage for raw YAML device metadata linting."""

from pathlib import Path
from typing import Any

import pytest

from scripts.check_device_configs import (
    CONFIG_DIR,
    main,
    validate_entity,
    validate_file,
)


@pytest.mark.parametrize(
    "data",
    [
        {"unit_of_measurement": "Volts"},
        {"unit_of_measurement": "Celsius"},
        {"unit_of_measurement": "°C", "device_class": "temperature_delta"},
        {"unit_of_measurement": "%", "state_class": "measurement"},
        {"unit_of_measurement": "rpm", "state_class": "measurement"},
        {"unit_of_measurement": "°", "state_class": "measurement_angle"},
        {"unit_of_measurement": "rpm", "state_class": None},
        {
            "unit_of_measurement": "kvarh",
            "device_class": "reactive_energy",
            "state_class": "total",
        },
        {"name": "Power Factor", "device_class": "power_factor"},
        {
            "control": "number",
            "device_class": "carbon_dioxide",
            "unit_of_measurement": "ppm",
        },
        {"control": "binary_sensor", "device_class": "problem"},
        {"control": "switch", "device_class": "outlet"},
        {"string": True},
        {
            "string": True,
            "device_class": "enum",
            "options": ["running", "stopped"],
        },
        {},
    ],
)
def test_valid_metadata(data: dict[str, Any]) -> None:
    """Defaults and intentionally classless quantities remain valid."""
    assert not validate_entity("reading", data, "sensor")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"device_class": "co2"}, "invalid device_class"),
        ({"device_class": ["voltage"]}, "invalid device_class"),
        (
            {"control": "binary_sensor", "device_class": "voltage"},
            "invalid device_class",
        ),
        (
            {"control": "number", "state_class": "measurement"},
            "only supported for sensors",
        ),
        ({"control": "nonsense"}, "invalid control"),
        ({"unit_of_measurement": 12}, "must be a string"),
        ({"state_class": ["measurement"]}, "invalid state_class"),
        ({"state_class": "nonsense"}, "invalid state_class"),
        ({"unit_of_measurement": "°C"}, "expected device_class"),
        ({"name": "Phase 1 Power Factor"}, "expected device_class"),
        (
            {"unit_of_measurement": "Volts", "device_class": None},
            "expected device_class",
        ),
        (
            {"unit_of_measurement": "V", "device_class": "current"},
            "invalid for sensor class",
        ),
        (
            {
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "total",
            },
            "invalid for 'voltage'",
        ),
        (
            {"unit_of_measurement": "kvarh", "device_class": "reactive_energy"},
            "invalid for 'reactive_energy'",
        ),
        (
            {"unit_of_measurement": "kVArh", "device_class": "reactive_energy"},
            "use unit 'kvarh'",
        ),
        ({"string": True, "state_class": "measurement"}, "string values"),
        ({"string": True, "device_class": "voltage"}, "numeric classes"),
        ({"string": True, "unit_of_measurement": "%"}, "cannot declare units"),
        (
            {
                "string": True,
                "device_class": "enum",
                "options": ["running"],
                "state_class": "measurement",
            },
            "statistics",
        ),
        (
            {
                "string": True,
                "device_class": "enum",
                "options": ["running"],
                "unit_of_measurement": "%",
            },
            "cannot declare units",
        ),
        (
            {"unit_of_measurement": "rpm", "state_class": "measurement_angle"},
            "invalid for state_class",
        ),
        ({"state_class": "measurement_angle"}, "invalid for state_class"),
    ],
)
def test_invalid_metadata(data: dict[str, Any], message: str) -> None:
    """Reject bad raw values even if the integration loader would drop them."""
    assert any(message in error for error in validate_entity("reading", data, "sensor"))


@pytest.mark.parametrize("options", [None, [], [1], {0: "running"}, "running"])
def test_enum_string_requires_options(options: Any) -> None:
    """Enum string sensors require valid HA options rather than select mappings."""
    errors = validate_entity(
        "status",
        {"string": True, "device_class": "enum", "options": options},
        "sensor",
    )
    assert any("non-empty list of strings" in error for error in errors)


def test_shipped_configs() -> None:
    """All shipped configs satisfy the metadata lint contract."""
    errors = [
        error for path in CONFIG_DIR.glob("*.yaml") for error in validate_file(path)
    ]
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    "content", ["[", "- item", "read_only_word: []", "read_only_word:\n  bad: 1"]
)
def test_invalid_file(tmp_path: Path, content: str) -> None:
    """Malformed files return contextual diagnostics instead of being skipped."""
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    assert validate_file(path)
    assert main([str(path)]) == 1


def test_command_accepts_selected_files() -> None:
    """The command can check all configs or a selected config."""
    assert main() == 0
    assert main([str(CONFIG_DIR / "SDM630.yaml")]) == 0


def test_missing_file(tmp_path: Path) -> None:
    """A missing selected file fails validation."""
    assert main([str(tmp_path / "missing.yaml")]) == 1
