"""Coordinator tests"""
import asyncio
from unittest.mock import MagicMock, patch

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusSensorEntityDescription,
)


async def test_update_single():
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    entities = [
        ModbusContext(1, ModbusSensorEntityDescription(register_address=1, key="test"))
    ]

    response = {"test": MagicMock()}
    coordinator.max_read_size = 1
    coordinator.started = True
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with patch(
        "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.conversion.Conversion.convert_from_registers"
        ) as convert:
            convert.return_value = "Result"
            await coordinator._async_update_data()  # pylint: disable=protected-access
            convert.assert_called_once_with(
                desc=entities[0].desc, registers=response["test"].registers
            )


async def test_update_multiple():
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    entities = [
        ModbusContext(
            1, ModbusSensorEntityDescription(register_address=1, key="test1")
        ),
        ModbusContext(
            1, ModbusSensorEntityDescription(register_address=2, key="test2")
        ),
    ]

    response = {"test1": MagicMock(), "test2": MagicMock()}
    coordinator.max_read_size = 1
    coordinator.started = True
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with patch(
        "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.conversion.Conversion.convert_from_registers"
        ) as convert:
            convert.return_value = "Result"
            await coordinator._async_update_data()  # pylint: disable=protected-access
            assert convert.call_count == 2


async def test_update_exception():
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    entities = [
        ModbusContext(
            1, ModbusSensorEntityDescription(register_address=1, key="test1")
        ),
        ModbusContext(
            1, ModbusSensorEntityDescription(register_address=2, key="test2")
        ),
    ]

    response = {"test1": MagicMock(), "test2": MagicMock()}
    coordinator.max_read_size = 1
    coordinator.started = True
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with patch(
        "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        with patch(
            "custom_components.modbus_local_gateway.sensor_types.conversion.Conversion.convert_from_registers"
        ) as convert:
            convert.side_effect = ["Result", Exception()]
            await coordinator._async_update_data()  # pylint: disable=protected-access
            assert convert.call_count == 2
