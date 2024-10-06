"""Device info Tests"""

from unittest.mock import patch

import pytest
import yaml

from custom_components.modbus_local_gateway.sensor_types.device_loader import (
    load_devices,
)
from custom_components.modbus_local_gateway.sensor_types.modbus_device_info import (
    ModbusDeviceInfo,
)


def test_entity_load() -> None:
    """Test device loading"""
    yaml_txt = """device:
        model: Model
        manufacturer: Manufacturer

entities:
  entity:
    title: Title
    address: 1"""

    with patch(
        "custom_components.modbus_local_gateway.sensor_types.modbus_device_info.load_yaml"
    ) as load_yaml:
        load_yaml.return_value = yaml.full_load(yaml_txt)
        device = ModbusDeviceInfo("test.yaml")

        entities = device.entity_desciptions
        assert len(entities) == 1
        assert device.model == "Model"
        assert device.manufacturer == "Manufacturer"


def test_entity_entity_create_basic() -> None:
    """Test entity create basic"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {"title": "Title", "address": 1},
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")

        entities = device.entity_desciptions
        assert len(entities) == 1
        assert entities[0].name == "Title"
        assert entities[0].register_address == 1


def test_entity_entity_create_all_fields() -> None:
    """Test entity create entry all fields populated"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {
                    "title": "Title",
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
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types"
            ".base.ModbusSensorEntityDescription.validate",
            return_value=True,
        ):
            entities = device.entity_desciptions
            assert len(entities) == 1
            assert entities[0].name == "Title"
            assert entities[0].register_address == 1
            assert entities[0].float
            assert not entities[0].string
            assert entities[0].bits == 8
            assert entities[0].bit_shift == 2
            assert entities[0].register_multiplier == 10
            assert entities[0].register_count == 4
            assert entities[0].icon == "mdi:icon"
            assert entities[0].suggested_display_precision == 2  # type: ignore
            assert entities[0].register_map == {1: "One"}
            assert entities[0].state_class == "total"  # type: ignore
            assert entities[0].device_class == "A"
            assert entities[0].native_unit_of_measurement == "%"  # type: ignore
            assert entities[0].flags == {1: "One"}


def test_entity_entity_invalid_string_float() -> None:
    """Test entity invalid desc"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {"title": "Title", "address": 1, "string": True, "float": True},
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.base._LOGGER.warning"
        ) as log:
            entities = device.entity_desciptions
            log.assert_called_once()
            assert len(entities) == 0


def test_entity_entity_invalid_address() -> None:
    """Test entity desc"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {"title": "Test"},
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.modbus_device_info._LOGGER.error"
        ) as log:
            entities = device.entity_desciptions
            log.assert_called_once()
            assert len(entities) == 0


def test_entity_entity_invalid_float1() -> None:
    """Test entity desc"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {"title": "Test", "address": 1, "float": True, "size": 1},
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.base._LOGGER.warning"
        ) as log:
            entities = device.entity_desciptions
            log.assert_called_once()
            assert len(entities) == 0


def test_entity_entity_invalid_float2() -> None:
    """Test entity desc"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {
                    "title": "Test",
                    "address": 1,
                    "float": True,
                    "size": 2,
                    "bits": 4,
                },
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.base._LOGGER.warning"
        ) as log:
            entities = device.entity_desciptions
            log.assert_called_once()
            assert len(entities) == 0


def test_entity_entity_invalid_string() -> None:
    """Test entity desc"""

    def __init__(self, _):
        """Mocked init"""
        self._config = {  # pylint: disable=protected-access
            "entities": {
                "test": {
                    "title": "Test",
                    "address": 1,
                    "string": True,
                    "size": 2,
                    "bits": 4,
                },
            },
        }

    with patch.object(
        ModbusDeviceInfo,
        "__init__",
        __init__,
    ):
        device = ModbusDeviceInfo("test.yaml")
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.base._LOGGER.warning"
        ) as log:
            entities = device.entity_desciptions
            log.assert_called_once()
            assert len(entities) == 0


@pytest.mark.nohomeassistant
async def test_devices_yaml(hass) -> None:
    """Validate yaml files"""
    with patch(
        "custom_components.modbus_local_gateway.sensor_types.device_loader._LOGGER.error"
    ) as log:
        devices: dict[str, ModbusDeviceInfo] = await load_devices(hass=hass)
        log.assert_not_called()

    for name in devices:
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.modbus_device_info._LOGGER.warning"
        ) as log:
            _ = devices[name].entity_desciptions
            log.assert_not_called()
            _ = devices[name].properties
            log.assert_not_called()
            _ = devices[name].manufacturer
            log.assert_not_called()
            _ = devices[name].model
            log.assert_not_called()
