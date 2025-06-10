"""Coordinator tests"""

import asyncio
from datetime import timedelta
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

# pylint: disable=protected-access
# pylint: disable=unexpected-keyword-arg


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
            ModbusSensorEntityDescription(
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
            await coordinator._async_update_data()
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
            ModbusSensorEntityDescription(
                register_address=1,
                key="test1",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
        ModbusContext(
            1,
            ModbusSensorEntityDescription(
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
            await coordinator._async_update_data()
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
            ModbusSensorEntityDescription(
                register_address=1,
                key="test1",
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
        ),
        ModbusContext(
            1,
            ModbusSensorEntityDescription(
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
        await coordinator._async_update_data()
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
        await coordinator._async_update_data()
        assert convert.call_count == 2


async def test_write_data_success() -> None:
    """Test write_data calls client.write_data and requests refresh on success."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock()
    coordinator.async_update_entity = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=2,
            key="test2",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    entity._handle_coordinator_update = MagicMock()

    await entity.write_data("value")
    coordinator.client.write_data.assert_called_once_with(ctx, "value")
    coordinator.async_update_entity.assert_called_once()
    entity._handle_coordinator_update.assert_called_once()


async def test_write_data_raises() -> None:
    """Test write_data logs and raises UpdateFailed on exception."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock(side_effect=Exception("fail"))
    coordinator.async_request_refresh = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
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
        ModbusSensorEntityDescription(
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

    desc = ModbusSensorEntityDescription(
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

    desc = ModbusSensorEntityDescription(
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

    desc = ModbusSensorEntityDescription(
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
    desc = ModbusSensorEntityDescription(
        register_address=10,
        key="test_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(2, desc)
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    assert entity._attr_unique_id == "2-test_key"
    assert entity._attr_device_info == device
    assert entity.coordinator is coordinator


def test_modbus_coordinator_entity_init_raises_typeerror_on_invalid_desc() -> None:
    """Test ModbusCoordinatorEntity __init__ raises TypeError
    if desc is not ModbusEntityDescription."""
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
    assert coordinator._gateway == gateway
    assert coordinator._max_read_size == 1
    assert coordinator._gateway_device is gateway_device
    assert coordinator.gateway_device is gateway_device
    assert coordinator.gateway == gateway
    assert coordinator.max_read_size == 1


def test_modbus_coordinator_max_read_size_property_and_setter() -> None:
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


async def test_async_update_if_not_in_progress_locked() -> None:
    """Test _async_update_if_not_in_progress does nothing if lock is held."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    # Patch lock to simulate locked state
    entity._update_lock = MagicMock()
    entity._update_lock.locked.return_value = True
    entity.name = "test_entity"
    # Should not call _async_update_write_state
    with patch.object(entity, "_async_update_write_state") as mock_update:
        await entity._async_update_if_not_in_progress()
        mock_update.assert_not_called()


async def test_async_update_if_not_in_progress_unlocked() -> None:
    """Test _async_update_if_not_in_progress calls update if not locked."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    entity._update_lock = MagicMock()
    entity._update_lock.locked.return_value = False
    with patch.object(entity, "_async_update_write_state") as mock_update:
        await entity._async_update_if_not_in_progress()
        mock_update.assert_called_once()


def test_async_schedule_future_update_and_cancel() -> None:
    """Test _async_schedule_future_update schedules and cancels future update."""

    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    entity.hass = MagicMock()
    called = False

    def fake_cancel_call() -> None:
        nonlocal called
        called = True

    with patch(
        "custom_components.modbus_local_gateway.coordinator.async_call_later",
    ) as mock_call_later:
        mock_call_later.return_value = fake_cancel_call
        entity._cancel_call = None
        entity._async_schedule_future_update(5)
        print(mock_call_later)
        assert entity._cancel_call == fake_cancel_call  # pylint: disable=comparison-with-callable
        assert mock_call_later.called
        mock_call_later.assert_called_once_with(
            entity.hass, 5, entity._async_update_if_not_in_progress
        )
        # Now test cancel
        entity._async_cancel_future_pending_update()
        assert called


def test_async_cancel_update_polling() -> None:
    """Test _async_cancel_update_polling cancels timer if set."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)

    cancelled = False

    def cancel_timer() -> None:
        nonlocal cancelled
        cancelled = True

    entity._cancel_timer = cancel_timer
    entity._async_cancel_update_polling()
    assert entity._cancel_timer is None
    assert cancelled is True


async def test_async_run_sets_available_and_schedules() -> None:
    """Test async_run schedules update and sets available."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test",
        data_type=ModbusDataType.INPUT_REGISTER,
        scan_interval=1,
    )
    ctx = ModbusContext(1, desc)
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)
    entity.hass = MagicMock()
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator.async_call_later",
        ) as mock_call_later,
        patch(
            "custom_components.modbus_local_gateway.coordinator.async_track_time_interval",
        ) as mock_track_time_interval,
    ):
        entity.async_write_ha_state = MagicMock()
        entity._async_cancel_update_polling = MagicMock()

        entity.async_run()
        assert entity._attr_available is True
        assert entity._cancel_timer is not None
        assert entity._cancel_call is not None

        mock_call_later.assert_called_once_with(
            entity.hass, 0.1, entity._async_update_if_not_in_progress
        )
        mock_track_time_interval.assert_called_once_with(
            entity.hass,
            entity._async_update_if_not_in_progress,
            timedelta(seconds=float(1)),
        )
        entity.async_write_ha_state.assert_called_once()


async def test_async_added_to_hass_calls_super_and_run() -> None:
    """Test async_added_to_hass calls super and async_run."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)

    entity.async_run = AsyncMock(name="async_run")
    with patch(
        "custom_components.modbus_local_gateway.coordinator.CoordinatorEntity.async_added_to_hass"
    ) as mock_super:
        mock_super.return_value = AsyncMock()
        await entity.async_added_to_hass()
        mock_super.assert_called_once()
        entity.async_run.assert_called_once()


async def test_async_will_remove_from_hass_calls_super_and_cancels() -> None:
    """Test async_will_remove_from_hass calls super and cancels."""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusCoordinatorEntity(coordinator, ctx, device)

    entity._async_cancel_update_polling = AsyncMock()
    entity._async_cancel_future_pending_update = AsyncMock()
    with patch(
        "custom_components.modbus_local_gateway.coordinator.CoordinatorEntity"
        ".async_will_remove_from_hass"
    ) as mock_super:
        await entity.async_will_remove_from_hass()
        entity._async_cancel_update_polling.assert_called_once()
        entity._async_cancel_future_pending_update.assert_called_once()
        mock_super.assert_called_once()


async def test_async_update_entity() -> None:
    """Test async_update_entity calls _update_device."""
    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    ctx1 = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test1",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    ctx2 = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test2",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    coordinator._update_device = AsyncMock()
    coordinator._update_device.return_value = None
    await coordinator.async_update_entity(ctx1)
    coordinator._update_device.assert_called_once()

    coordinator._update_device.return_value = {"test1": "value1"}
    await coordinator.async_update_entity(ctx1)
    assert coordinator.data == {"test1": "value1"}

    coordinator._update_device.return_value = {"test2": "value2"}
    await coordinator.async_update_entity(ctx2)
    assert coordinator.data == {"test1": "value1", "test2": "value2"}

    coordinator._update_device.return_value = {"test2": "value3"}
    await coordinator.async_update_entity(ctx2)
    assert coordinator.data == {"test1": "value1", "test2": "value3"}
