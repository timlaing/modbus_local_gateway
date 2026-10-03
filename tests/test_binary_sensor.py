"""Binary Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.modbus_local_gateway.binary_sensor import (
    ModbusBinarySensorEntity,
    async_setup_entry,
)
from custom_components.modbus_local_gateway.const import (
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusBinarySensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)

from .conftest import mock_gateway_entry


@pytest.mark.asyncio
async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test the HA setup function"""
    entry = mock_gateway_entry(host="127.0.0.1", port=1234, filename="test.yaml")
    callback = MagicMock()
    coordinator = AsyncMock()
    gw_dev = MagicMock()
    type(coordinator).gateway_device = PropertyMock(return_value=gw_dev)
    identifiers = PropertyMock()
    identifiers.return_value = ["a"]
    type(gw_dev).identifiers = identifiers
    subentry_id = next(
        iter(entry.get_subentries_of_type(SUBENTRY_TYPE_DEVICE))
    ).subentry_id
    entry.runtime_data = {subentry_id: coordinator}

    pm1 = PropertyMock(
        return_value=[
            ModbusBinarySensorEntityDescription(
                key="discrete_ro",
                register_address=1,
                data_type=ModbusDataType.DISCRETE_INPUT,
                control_type="binary_sensor",
            ),
        ]
    )
    pm2 = PropertyMock(return_value="")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management"
            ".modbus_device_info.load_yaml",
            return_value={"device": MagicMock()},
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"test.yaml": MagicMock()},
        ),
        patch.object(modbus_device_info.ModbusDeviceInfo, "entity_descriptions", pm1),
        patch.object(modbus_device_info.ModbusDeviceInfo, "manufacturer", pm2),
        patch.object(modbus_device_info.ModbusDeviceInfo, "model", pm2),
    ):
        coordinator.device_info = modbus_device_info.ModbusDeviceInfo("test.yaml")
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert len(callback.add.call_args[0][0]) == 1
        assert callback.add.call_args[1] == {
            "update_before_add": False,
            "config_subentry_id": subentry_id,
        }
        pm1.assert_called_once()


@pytest.mark.asyncio
async def test_update_none() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.side_effect = Exception()

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_called_once()


@pytest.mark.asyncio
async def test_update_value_bool() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
            on=True,
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = True
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_not_called()
        write.assert_called_once()
        assert entity.is_on is True


@pytest.mark.asyncio
async def test_update_value_int() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusBinarySensorEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.DISCRETE_INPUT,
            control_type="binary_sensor",
            on=10,
        ),
    )
    device = MagicMock()
    entity = ModbusBinarySensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, type(entity)).name = PropertyMock(return_value="Test")
    coordinator.get_data.return_value = 10
    write = MagicMock()
    cast(Any, entity).async_write_ha_state = write

    with patch(
        "custom_components.modbus_local_gateway.binary_sensor._LOGGER.error"
    ) as error:
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        error.assert_not_called()
        write.assert_called_once()
        assert entity.is_on is True
