"""Device info Tests"""

from unittest.mock import patch

import pytest
import yaml

from custom_components.modbus_local_gateway.entity_management.device_loader import load_devices
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import ModbusDeviceInfo
from custom_components.modbus_local_gateway.entity_management.const import ModbusDataType


def test_entity_load() -> None:
    """Test device loading"""
    yaml_txt = """device:
        model: Model
        manufacturer: Manufacturer

read_write_word:
  entity_rw:
    name: Read-Write Entity
    address: 1

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
        "custom_components.modbus_local_gateway.sensor_types.modbus_device_info.load_yaml"
    ) as load_yaml:
        load_yaml.return_value = yaml.full_load(yaml_txt)
        device = ModbusDeviceInfo("test.yaml")

        entities = device.entity_descriptions
        assert len(entities) == 4
        assert device.model == "Model"
        assert device.manufacturer == "Manufacturer"
        assert any(e.key == "entity_rw" and e.data_type == ModbusDataType.HOLDING_REGISTER for e in entities)
        assert any(e.key == "entity_ro" and e.data_type == ModbusDataType.INPUT_REGISTER for e in entities)
        assert any(e.key == "coil_rw" and e.data_type == ModbusDataType.COIL for e in entities)
        assert any(e.key == "discrete_ro" and e.data_type == ModbusDataType.DISCRETE_INPUT for e in entities)


def test_entity_create_basic() -> None:
    """Test basic entity creation for all data types"""
    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "device": {"manufacturer": "Test", "model": "Test"},
            "read_write_word": {"test_rw": {"name": "Title RW", "address": 1}},
            "read_only_word": {"test_ro": {"name": "Title RO", "address": 2}},
            "read_write_boolean": {"test_coil": {"name": "Title Coil", "address": 3, "control": "switch"}},
            "read_only_boolean": {"test_discrete": {"name": "Title Discrete", "address": 4}},
        }

    with patch.object(ModbusDeviceInfo, "__init__", __init__):
        device = ModbusDeviceInfo("test.yaml")
        entities = device.entity_descriptions
        assert len(entities) == 4
        assert any(e.name == "Title RW" and e.register_address == 1 and e.data_type == ModbusDataType.HOLDING_REGISTER for e in entities)
        assert any(e.name == "Title RO" and e.register_address == 2 and e.data_type == ModbusDataType.INPUT_REGISTER for e in entities)
        assert any(e.name == "Title Coil" and e.register_address == 3 and e.data_type == ModbusDataType.COIL for e in entities)
        assert any(e.name == "Title Discrete" and e.register_address == 4 and e.data_type == ModbusDataType.DISCRETE_INPUT for e in entities)


def test_entity_create_all_fields() -> None:
    """Test entity creation with all fields for a Holding Register"""
    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
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

    with patch.object(ModbusDeviceInfo, "__init__", __init__):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.base.ModbusSensorEntityDescription.validate",
            return_value=True,
        ):
            entities = device.entity_descriptions
            assert len(entities) == 1
            entity = entities[0]
            assert entity.name == "Title"
            assert entity.register_address == 1
            assert entity.is_float
            assert not entity.is_string
            assert entity.conv_bits == 8
            assert entity.conv_shift_bits == 2
            assert entity.conv_multiplier == 10
            assert entity.register_count == 2
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
    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "device": {"manufacturer": "Test", "model": "Test"},
            "read_write_word": {"test": {"name": "Title", "address": 1, "string": True, "float": True}},
            "read_only_word": {},
            "read_write_boolean": {},
            "read_only_boolean": {},
        }

    with patch.object(ModbusDeviceInfo, "__init__", __init__):
        device = ModbusDeviceInfo("test.yaml")
        with patch("custom_components.modbus_local_gateway.sensor_types.base._LOGGER.warning") as log:
            entities = device.entity_descriptions
            log.assert_called_once()
            assert len(entities) == 0


def test_entity_invalid_address() -> None:
    """Test entity missing address"""
    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "device": {"manufacturer": "Test", "model": "Test"},
            "read_write_word": {"test": {"name": "Test"}},
            "read_only_word": {},
            "read_write_boolean": {},
            "read_only_boolean": {},
        }

    with patch.object(ModbusDeviceInfo, "__init__", __init__):
        device = ModbusDeviceInfo("test.yaml")
        with patch("custom_components.modbus_local_gateway.sensor_types.modbus_device_info._LOGGER.error") as log:
            entities = device.entity_descriptions
            log.assert_not_called()  # No error logged, just skipped
            assert len(entities) == 0


def test_entity_invalid_control_type() -> None:
    """Test entity with invalid control type for data type"""
    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "device": {"manufacturer": "Test", "model": "Test"},
            "read_only_word": {"test": {"name": "Test", "address": 1, "control": "switch"}},
            "read_write_word": {},
            "read_write_boolean": {},
            "read_only_boolean": {},
        }

    with patch.object(ModbusDeviceInfo, "__init__", __init__):
        device = ModbusDeviceInfo("test.yaml")
        with patch("custom_components.modbus_local_gateway.sensor_types.modbus_device_info._LOGGER.warning") as log:
            entities = device.entity_descriptions
            log.assert_called_once()
            assert len(entities) == 0


@pytest.mark.nohomeassistant
async def test_devices_yaml(hass) -> None:
    """Validate yaml files with new structure"""
    with patch("custom_components.modbus_local_gateway.sensor_types.device_loader._LOGGER.error") as log:
        devices: dict[str, ModbusDeviceInfo] = await load_devices(hass=hass)
        log.assert_not_called()

    for name in devices:
        with patch("custom_components.modbus_local_gateway.sensor_types.modbus_device_info._LOGGER.warning") as log:
            _ = devices[name].entity_descriptions
            log.assert_not_called()
            _ = devices[name].manufacturer
            log.assert_not_called()
            _ = devices[name].model
            log.assert_not_called()
