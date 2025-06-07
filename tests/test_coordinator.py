"""Coordinator tests"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import (
    ModbusCoordinator,
    ModbusCoordinatorEntity,
    UpdateFailed,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDataType,
    ModbusSensorEntityDescription,
)


async def test_update_single() -> None:
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

    entities: list[ModbusContext] = [
        ModbusContext(
            1,
            ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=1,
                key="test",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        )
    ]

    response = {"test": MagicMock()}
    coordinator.max_read_size = 1
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with patch(
        "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        with patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert:
            convert.return_value = "Result"
            await coordinator._async_update_data()  # pylint: disable=protected-access
            convert.assert_called_once_with(
                desc=entities[0].desc, response=response["test"]
            )


async def test_update_multiple() -> None:
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

    entities: list[ModbusContext] = [
        ModbusContext(
            1,
            ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=1,
                key="test1",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
        ModbusContext(
            1,
            ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=2,
                key="test2",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
    ]

    response = {"test1": MagicMock(), "test2": MagicMock()}
    coordinator.max_read_size = 1
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with patch(
        "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        with patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert:
            convert.return_value = "Result"
            await coordinator._async_update_data()  # pylint: disable=protected-access
            assert convert.call_count == 2


async def test_update_exception() -> None:
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

    entities: list[ModbusContext] = [
        ModbusContext(
            1,
            ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=1,
                key="test1",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
        ModbusContext(
            1,
            ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                register_address=2,
                key="test2",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
    ]

    response = {"test1": MagicMock(), "test2": MagicMock()}
    coordinator.max_read_size = 1
    future = asyncio.Future()
    future.set_result(response)
    client.update_slave.return_value = future
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
            return_value=entities,
        ),
        patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert,
    ):
        convert.side_effect = ["Result", Exception()]
        await coordinator._async_update_data()  # pylint: disable=protected-access
        assert convert.call_count == 2

    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator.ModbusCoordinator.async_contexts",
            return_value=entities,
        ),
        patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert,
        pytest.raises(UpdateFailed),
    ):
        convert.side_effect = [Exception(), Exception()]
        await coordinator._async_update_data()  # pylint: disable=protected-access
        assert convert.call_count == 2


async def test_write_data_success() -> None:
    """Test write_data calls client.write_data and requests refresh on success."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=2,
            key="test2",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)

    await entity.write_data("value")
    coordinator.client.write_data.assert_called_once_with(ctx, "value")
    coordinator.async_request_refresh.assert_called_once()


async def test_write_data_raises() -> None:
    """Test write_data logs and raises UpdateFailed on exception."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock(side_effect=Exception("fail"))
    coordinator.async_request_refresh = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=2,
            key="test2",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)

    with pytest.raises(UpdateFailed):
        await entity.write_data("value")
    coordinator.client.write_data.assert_called_once_with(ctx, "value")
    # async_request_refresh should not be called if exception occurs
    coordinator.async_request_refresh.assert_not_called()


def test_entity_description_property() -> None:
    """Test entity_description property returns context description."""

    coordinator = MagicMock()
    device = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
            register_address=2,
            key="test2",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    assert entity.entity_description is ctx.desc


def test_get_data_returns_value() -> None:
    """Test get_data returns the correct value when present in data."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    desc = ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        register_address=1,
        key="test_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)
    coordinator.data = {"test_key": 42}
    assert coordinator.get_data(ctx) == 42


def test_get_data_returns_none_when_data_is_none() -> None:
    """Test get_data returns None if self.data is None."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    desc = ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        register_address=1,
        key="test_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)
    coordinator.data = {}
    assert coordinator.get_data(ctx) is None


def test_get_data_returns_none_when_key_not_in_data() -> None:
    """Test get_data returns None if key is not in self.data."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    desc = ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        register_address=1,
        key="missing_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)
    coordinator.data = {"other_key": 123}
    assert coordinator.get_data(ctx) is None


def test_modbus_coordinator_entity_init_sets_attributes() -> None:
    """Test ModbusCoordinatorEntity __init__ sets attributes correctly."""
    coordinator = MagicMock()
    device = MagicMock()
    desc = ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
        register_address=10,
        key="test_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(2, desc)
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    assert entity._attr_unique_id == "2-test_key"  # pylint: disable=protected-access
    assert entity._attr_device_info == device  # pylint: disable=protected-access
    assert entity.coordinator is coordinator


def test_modbus_coordinator_entity_init_raises_typeerror_on_invalid_desc() -> None:
    """Test ModbusCoordinatorEntity __init__ raises TypeError if desc is not ModbusEntityDescription."""
    coordinator = MagicMock()
    device = MagicMock()

    class DummyDesc:
        """Dummy description class that does not inherit from ModbusEntityDescription."""

        key: str = "bad"

    ctx = ModbusContext(1, DummyDesc())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ModbusCoordinatorEntity(coordinator, ctx, device)


def test_modbus_coordinator_init_sets_attributes() -> None:
    """Test ModbusCoordinator __init__ sets attributes correctly."""
    hass = MagicMock()
    gateway_device = MagicMock()
    client = MagicMock()
    gateway = "GW"
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway_device,
        client=client,
        gateway=gateway,
        update_interval=42,
    )
    assert coordinator.client is client
    assert coordinator._gateway == gateway  # pylint: disable=protected-access
    assert coordinator._max_read_size == 1  # pylint: disable=protected-access
    assert coordinator._gateway_device is gateway_device  # pylint: disable=protected-access
    assert coordinator.gateway_device is gateway_device
    assert coordinator.gateway == gateway
    assert coordinator.max_read_size == 1


def test_modbus_coordinator_max_read_size_property_and_setter():
    """Test ModbusCoordinator max_read_size property and setter."""
    hass = MagicMock()
    gateway_device = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway_device,
        client=client,
        gateway="GW",
    )
    assert coordinator.max_read_size == 1
    coordinator.max_read_size = 5
    assert coordinator.max_read_size == 5
