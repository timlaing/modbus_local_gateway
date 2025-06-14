"""Device info Tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import patch

import pytest
import yaml
from pytest import LogCaptureFixture

from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.entity_management.device_loader import (
    load_devices,
)
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import (
    ModbusDeviceInfo,
)


def test_entity_load() -> None:
    """Test device loading"""
    yaml_txt = """device:
        model: Model
        manufacturer: Manufacturer

read_write_word:
  entity_rw:
    name: Read-Write Entity
    address: 1

  entity_invalid_bits:
    name: Entity Invalid Bits
    address: 2
    control: switch
    bits: 1

  entity_invalid_shift:
    name: Entity Invalid Shift
    address: 3
    control: switch
    shift_bits: 1

  entity_invalid_switch:
    name: Entity Invalid Switch
    address: 4
    control: switch
    switch: true

  entity_text:
    name: Entity Text
    address: 5
    control: text

read_only_word:
  entity_ro:
    name: Read-Only Entity
    address: 2

read_write_boolean:
  coil_rw:
    name: Coil RW
    address: 3
    control: switch

read_only_boolean:
  discrete_ro:
    name: Discrete RO
    address: 4"""

    with patch(
        "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml"
    ) as load_yaml:
        load_yaml.return_value = yaml.full_load(yaml_txt)
        device = ModbusDeviceInfo("test.yaml")

        entities = device.entity_descriptions
        assert len(entities) == 5
        assert device.model == "Model"
        assert device.manufacturer == "Manufacturer"
        assert any(
            e.key == "entity_rw" and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert any(
            e.key == "entity_ro" and e.data_type == ModbusDataType.INPUT_REGISTER
            for e in entities
        )
        assert any(
            e.key == "coil_rw" and e.data_type == ModbusDataType.COIL for e in entities
        )
        assert any(
            e.key == "discrete_ro" and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert any(
            e.key == "entity_text" and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_bits"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_shift"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert not any(
            e.key == "entity_invalid_switch"
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )


def test_entity_create_basic() -> None:
    """Test basic entity creation for all data types"""

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {"test_rw": {"name": "Title RW", "address": 1}},
        "read_only_word": {"test_ro": {"name": "Title RO", "address": 2}},
        "read_write_boolean": {
            "test_coil": {"name": "Title Coil", "address": 3, "control": "switch"}
        },
        "read_only_boolean": {
            "test_discrete1": {"name": "Title Discrete 1", "address": 4},
            "test_discrete2": {"name": "Title Discrete 2", "address": 5, "bits": 1},
            "test_discrete3": {
                "name": "Title Discrete 3",
                "address": 6,
                "shift_bits": 1,
            },
        },
    }

    with patch(
        "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml",
        return_value=_config,
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == 4
        assert any(
            e.name == "Test Title RW"
            and e.register_address == 1
            and e.data_type == ModbusDataType.HOLDING_REGISTER
            for e in entities
        )
        assert any(
            e.name == "Test Title RO"
            and e.register_address == 2
            and e.data_type == ModbusDataType.INPUT_REGISTER
            for e in entities
        )
        assert any(
            e.name == "Test Title Coil"
            and e.register_address == 3
            and e.data_type == ModbusDataType.COIL
            for e in entities
        )
        assert any(
            e.name == "Test Title Discrete 1"
            and e.register_address == 4
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert not any(
            e.name == "Test Title Discrete 2"
            and e.register_address == 5
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )
        assert not any(
            e.name == "Test Title Discrete 3"
            and e.register_address == 6
            and e.data_type == ModbusDataType.DISCRETE_INPUT
            for e in entities
        )


def test_entity_create_all_fields() -> None:
    """Test entity creation with all fields for a Holding Register"""

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {
            "test": {
                "name": "Title",
                "address": 1,
                "float": True,
                "string": False,
                "bits": 8,
                "shift_bits": 2,
                "multiplier": 10,
                "size": 4,
                "icon": "mdi:icon",
                "precision": 2,
                "map": {1: "One"},
                "state_class": "total",
                "device_class": "A",
                "unit_of_measurement": "%",
                "flags": {1: "One"},
            },
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.base."
            "ModbusSensorEntityDescription.validate",
            return_value=True,
        ),
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == 1
        assert isinstance(entities[0], ModbusSensorEntityDescription)
        entity: ModbusSensorEntityDescription = entities[0]
        assert entity.name == "Test Title"
        assert entity.register_address == 1
        assert entity.is_float
        assert not entity.is_string
        assert entity.conv_bits == 8
        assert entity.conv_shift_bits == 2
        assert entity.conv_multiplier == 10
        assert entity.register_count == 4
        assert entity.icon == "mdi:icon"
        assert entity.precision == 2
        assert entity.conv_map == {1: "One"}
        assert entity.state_class == "total"
        assert entity.device_class == "A"
        assert entity.native_unit_of_measurement == "%"
        assert entity.conv_flags == {1: "One"}
        assert entity.data_type == ModbusDataType.HOLDING_REGISTER


def test_entity_invalid_string_float() -> None:
    """Test invalid entity with both string and float"""

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {
            "test": {"name": "Title", "address": 1, "string": True, "float": True}
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
        ) as log,
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_called_once()
        assert len(entities) == 0


def test_entity_invalid_address() -> None:
    """Test entity missing address"""

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {"test": {"name": "Test"}},
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.error"
        ) as log,
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_not_called()  # No error logged, just skipped
        assert len(entities) == 0


def test_entity_invalid_control_type() -> None:
    """Test entity with invalid control type for data type"""

    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_only_word": {"test": {"name": "Test", "address": 1, "control": "switch"}},
        "read_write_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.warning"
        ) as log,
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        log.assert_called_once()
        assert len(entities) == 0


@pytest.mark.parametrize(
    (
        "scan_interval",
        "num_entities",
        "log_message",
    ),
    [
        (None, 1, None),
        (10, 1, None),
        (0, 0, "scan_interval must be > 0"),
        (-5, 0, "scan_interval must be > 0"),
    ],
)
def test_validate_scan_interval(
    scan_interval: int | None,
    num_entities: int,
    log_message: str,
    caplog: LogCaptureFixture,
) -> None:
    """Test _validate_scan_interval with various scan_interval values."""
    _config = {
        "device": {"manufacturer": "Test", "model": "Test"},
        "read_write_word": {
            "test": {"name": "Test", "address": 1, "scan_interval": scan_interval}
        },
        "read_only_word": {},
        "read_write_boolean": {},
        "read_only_boolean": {},
    }
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value=_config,
        ),
        caplog.at_level("WARNING"),
    ):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == num_entities
        if log_message:
            assert log_message in caplog.text


@pytest.mark.asyncio
async def test_devices_yaml(hass) -> None:
    """Validate yaml files with new structure"""
    with patch(
        "custom_components.modbus_local_gateway.entity_management.device_loader._LOGGER.error"
    ) as log:
        devices: dict[str, ModbusDeviceInfo] = await load_devices(hass=hass)
        log.assert_not_called()

    for name in devices:
        with patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info._LOGGER.warning"
        ) as log:
            _ = devices[name].entity_descriptions
            log.assert_not_called()
            _ = devices[name].manufacturer
            log.assert_not_called()
            _ = devices[name].model
            log.assert_not_called()
