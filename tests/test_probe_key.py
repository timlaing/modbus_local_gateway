"""Which entity a recovery probe reads, and where that comes from."""

from copy import deepcopy
import logging
from typing import Any
from unittest.mock import patch

import pytest

from custom_components.modbus_local_gateway.entity_management import (
    modbus_device_info,
)

_PROBE_CONFIG: dict[str, Any] = {
    "device": {"manufacturer": "Test Manufacturer", "model": "Test Model"},
    "read_write_word": {"first": {"name": "First", "address": 1}},
    "read_only_word": {"status": {"name": "Status", "address": 2}},
    "read_write_boolean": {
        "relay": {"name": "Relay", "address": 3, "control": "switch"}
    },
    "composite": {"total": {"name": "Total", "fields": []}},
}


def _device_info(probe_key: str | None = None) -> modbus_device_info.ModbusDeviceInfo:
    """A device of a few data types, naming a recovery probe if asked to."""
    config = deepcopy(_PROBE_CONFIG)
    if probe_key is not None:
        config["device"]["probe_key"] = probe_key
    with patch(
        "custom_components.modbus_local_gateway.entity_management."
        "modbus_device_info.load_yaml",
        return_value=config,
    ):
        return modbus_device_info.ModbusDeviceInfo("test.yaml")


def test_probe_key_is_not_named_by_default() -> None:
    """Without a name, the probe reads the first entity of the poll."""
    assert _device_info().probe_key is None


def test_probe_key_is_the_entity_the_device_names() -> None:
    """A device whose first entity is a poor probe can name a better one."""
    assert _device_info("status").probe_key == "status"


def test_probe_key_may_be_an_entity_of_any_data_type() -> None:
    """A coil is as good a witness that a device is powered as a register is."""
    assert _device_info("relay").probe_key == "relay"


def test_probe_key_may_be_a_composite_entity() -> None:
    """A composite is an entity like any other, and can be the probe."""
    assert _device_info("total").probe_key == "total"


def test_probe_key_that_is_not_an_entity_of_the_device_falls_back(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A name that is not one of the device's entities cannot be read.

    The probe falls back to the first entity, which is what it would have done
    anyway, and says why: a name that is wrong in a device configuration is
    worth knowing about, and worth saying once rather than on every probe.
    """
    with caplog.at_level(logging.WARNING):
        device = _device_info("nonexistent")
        assert device.probe_key is None
        # Every poll asks for this, so it is decided once rather than logged once
        # per poll for as long as the device config says it.
        assert device.probe_key is None

    warnings = [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    assert "probe_key" in warnings[0].getMessage()
    assert "nonexistent" in warnings[0].getMessage()
