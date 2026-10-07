"""Coordinator tests"""

# pylint: disable=too-many-lines, unexpected-keyword-arg, protected-access
import asyncio
from datetime import datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.conversion import ValueUnavailable
from custom_components.modbus_local_gateway.coordinator import (
    ModbusCoordinator,
    ModbusCoordinatorEntity,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusDateTimeEntityDescription,
    ModbusFieldDescription,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)


@pytest.mark.asyncio
async def test_update_single(mock_config_entry: ConfigEntry) -> None:
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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
    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result(response)
    client.update_device.return_value = future
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
            return_value=entities,
        ),
        patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert,
    ):
        convert.return_value = "Result"
        await coordinator._async_update_data()
        convert.assert_called_once_with(
            desc=entities[0].desc, response=response["test"]
        )


@pytest.mark.asyncio
async def test_update_composite(mock_config_entry: ConfigEntry) -> None:
    """A composite entity is assembled by the composite conversion"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
        gateway_device=gateway,
        client=client,
        gateway="Test",
    )

    entities: list[ModbusContext] = [
        ModbusContext(
            1,
            ModbusDateTimeEntityDescription(
                key="clock",
                register_address=1,
                register_count=2,
                data_type=ModbusDataType.HOLDING_REGISTER,
                control_type=ControlType.DATETIME,
                composite_type=CompositeType.TIME,
                fields=(
                    ModbusFieldDescription(key="hour", address=1),
                    ModbusFieldDescription(key="minute", address=2),
                ),
            ),
        )
    ]

    response = {"clock": MagicMock()}
    coordinator.max_read_size = 1
    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result(response)
    client.update_device.return_value = future
    converted = datetime(2026, 9, 22, 16, 30)
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
            return_value=entities,
        ),
        patch(
            "custom_components.modbus_local_gateway.composite.CompositeConversion"
            ".from_registers"
        ) as from_registers,
    ):
        from_registers.return_value = converted
        data = await coordinator._async_update_data()
        from_registers.assert_called_once()
        assert from_registers.call_args.args[0] == entities[0].desc
        assert from_registers.call_args.args[1] == response["clock"]
        assert data["clock"] == converted


@pytest.mark.asyncio
async def test_update_multiple(mock_config_entry: ConfigEntry) -> None:
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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
    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result(response)
    client.update_device.return_value = future
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
            return_value=entities,
        ),
        patch(
            "custom_components.modbus_local_gateway"
            ".conversion.Conversion.convert_from_response"
        ) as convert,
    ):
        convert.return_value = "Result"
        await coordinator._async_update_data()
        assert convert.call_count == 2


@pytest.mark.asyncio
async def test_update_exception(mock_config_entry: ConfigEntry) -> None:
    """Test the update functionality"""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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
    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result(response)
    client.update_device.return_value = future
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
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
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
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


@pytest.mark.asyncio
async def test_write_data_success() -> None:
    """Test write_data calls client.write_data and requests refresh on success."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock()
    coordinator.async_update_entity = AsyncMock()
    coordinator.write_function = WriteFunction.MULTIPLE
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
    cast(Any, entity)._handle_coordinator_update = MagicMock()

    await entity.write_data("value")
    coordinator.client.write_data.assert_called_once_with(
        ctx, "value", write_function=WriteFunction.MULTIPLE
    )
    cast(Any, coordinator).async_update_entity.assert_called_once()
    cast(Any, entity)._handle_coordinator_update.assert_called_once()


@pytest.mark.asyncio
async def test_write_data_raises() -> None:
    """Test write_data logs and raises UpdateFailed on exception."""

    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock(side_effect=Exception("fail"))
    coordinator.async_request_refresh = AsyncMock()
    coordinator.write_function = WriteFunction.SINGLE
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
    coordinator.client.write_data.assert_called_once_with(
        ctx, "value", write_function=WriteFunction.SINGLE
    )
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


def test_get_data_returns_value(mock_config_entry: ConfigEntry) -> None:
    """Test get_data returns the correct value when present in data."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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


def test_get_data_returns_none_when_data_is_none(
    mock_config_entry: ConfigEntry,
) -> None:
    """Test get_data returns None if self.data is None."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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


def test_get_data_returns_none_when_key_not_in_data(
    mock_config_entry: ConfigEntry,
) -> None:
    """Test get_data returns None if key is not in self.data."""

    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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
    coordinator = MagicMock(config_entry=MagicMock(data={}), prefix=None)
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
        """Dummy description class that does not inherit from
        ModbusEntityDescription.
        """

        key: str = "bad"

    ctx = ModbusContext(1, cast(Any, DummyDesc()))
    with pytest.raises(TypeError):
        ModbusCoordinatorEntity(coordinator, ctx, device)


def test_modbus_coordinator_init_sets_attributes(
    mock_config_entry: ConfigEntry,
) -> None:
    """Test ModbusCoordinator __init__ sets attributes correctly."""
    hass = MagicMock()
    gateway_device = MagicMock()
    client = MagicMock()
    gateway = "GW"
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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


def test_modbus_coordinator_max_read_size_property_and_setter(
    mock_config_entry: ConfigEntry,
) -> None:
    """Test ModbusCoordinator max_read_size property and setter."""
    hass = MagicMock()
    gateway_device = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
        gateway_device=gateway_device,
        client=client,
        gateway="GW",
    )
    assert coordinator.max_read_size == 1
    coordinator.max_read_size = 5
    assert coordinator.max_read_size == 5


@pytest.mark.asyncio
async def test_async_update_if_not_in_progress_locked(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test _async_update_if_not_in_progress does nothing if lock is held."""
    coordinator = AsyncMock()
    coordinator.async_update_entity = AsyncMock()
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
    entity._update_lock = asyncio.Lock()
    await entity._update_lock.acquire()  # Simulate lock being held
    entity.name = "test_entity"
    with caplog.at_level("DEBUG"):
        await entity._async_update_if_not_in_progress()
        coordinator.async_update_entity.assert_not_called()
        assert "Update for entity test_entity is already in progress" in caplog.text


@pytest.mark.asyncio
async def test_a_read_that_arrives_during_one_is_skipped_without_waiting(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A tick that lands mid-read is dropped, and does not queue a second read.

    #327: the lock used to be waited for with a 0.1 s deadline, so a tick that
    arrived just before a slow read finished waited for it and then read the
    entity a second time - the same value, from the same device, a moment after
    the read holding the lock was about to publish it. What holding the lock is,
    is a read of this entity, so there is nothing to wait for.
    """
    coordinator = AsyncMock()
    in_flight = asyncio.Event()
    reads: list[str] = []

    async def read_entity(_ctx: ModbusContext) -> None:
        """A read that takes a while, as a read of a slow device does."""
        reads.append("slow")
        in_flight.set()
        await asyncio.sleep(0.05)

    coordinator.async_update_entity = read_entity
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    entity = ModbusCoordinatorEntity(coordinator, ctx, MagicMock())
    entity._update_lock = asyncio.Lock()
    entity.name = "test_entity"

    first = asyncio.create_task(entity._read_data())
    await in_flight.wait()

    with (
        caplog.at_level("DEBUG"),
        patch.object(entity, "_handle_coordinator_update") as write_state,
    ):
        # This tick arrives while the read above is still in flight.
        assert await entity._read_data() is False

    await first

    # It neither waited for that read nor read the entity a second time.
    assert reads == ["slow"]
    assert "already in progress" in caplog.text
    write_state.assert_not_called()


@pytest.mark.asyncio
async def test_the_lock_is_released_when_a_read_of_the_entity_finishes() -> None:
    """A read can never be left holding the lock with nothing to release it.

    #327: waiting for the lock with a deadline could cancel an acquire that was
    granted in the same event loop iteration, and `asyncio.Lock` keeps that
    grant: the lock stayed held, every later read timed out, the timeout was
    swallowed as "already in progress", and the entity silently stopped updating
    for the rest of the session. Nothing here waits for the lock at all, so
    nothing can end up holding it on behalf of nobody - the entity keeps reading
    on every cycle after a skipped one.
    """
    coordinator = AsyncMock()
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    entity = ModbusCoordinatorEntity(coordinator, ctx, MagicMock())
    entity._update_lock = asyncio.Lock()
    entity.name = "test_entity"

    # A read in flight, a tick that arrives while it holds the lock, and then the
    # cycles after it: the lock is free between reads and every one of them reads.
    await entity._update_lock.acquire()
    assert await entity._read_data() is False
    entity._update_lock.release()

    for _ in range(3):
        assert await entity._read_data() is True
        assert not entity._update_lock.locked()

    assert coordinator.async_update_entity.await_count == 3


@pytest.mark.asyncio
async def test_the_read_back_after_a_write_waits_for_a_read_in_progress() -> None:
    """A write read-back is not dropped behind a read of the same entity.

    #327: skipping the read of an entity whose lock is held is right for a polling
    tick - the read holding the lock is about to publish that value - but a write
    has already put a new value in the device by then, and a read that started
    before the write has the old one in the cache. Skipping the read-back would
    leave the entity reporting the old value until the next poll, so the write
    waits for that read to finish.
    """
    coordinator = MagicMock()
    coordinator.client.write_data = AsyncMock()
    read_done = asyncio.Event()
    reads: list[str] = []

    async def read_entity(_ctx: ModbusContext) -> None:
        """The read that was already in flight when the device was written."""
        reads.append("in flight")
        await asyncio.sleep(0.02)
        read_done.set()

    coordinator.async_update_entity = read_entity
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    entity = ModbusCoordinatorEntity(coordinator, ctx, MagicMock())
    entity._update_lock = asyncio.Lock()
    entity.name = "test_entity"

    in_flight = asyncio.create_task(entity._read_data())
    await asyncio.sleep(0)

    with patch.object(entity, "_handle_coordinator_update") as write_state:
        write = asyncio.create_task(entity.write_data(1))
        await asyncio.sleep(0)

        # The read that was already running finishes first...
        await in_flight
        # ...and the read-back the write asked for follows it, not lost to the skip.
        await write

    assert read_done.is_set()
    assert reads == ["in flight", "in flight"]
    assert coordinator.client.write_data.await_count == 1
    write_state.assert_called_once()


@pytest.mark.asyncio
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
        assert entity._cancel_call is fake_cancel_call
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


@pytest.mark.asyncio
async def test_async_run_does_not_read_and_schedules_the_interval() -> None:
    """async_run leaves the first read to the coordinator.

    A read per entity is what held startup up on a gateway with a device that is
    switched off, so the entity does not read on its own here.
    """
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
            "custom_components.modbus_local_gateway.coordinator"
            ".async_track_time_interval",
        ) as mock_track_time_interval,
    ):
        cast(Any, entity)._async_cancel_update_polling = MagicMock()

        entity.async_run()
        assert entity._cancel_timer is not None

        mock_call_later.assert_not_called()
        mock_track_time_interval.assert_called_once_with(
            entity.hass,
            entity._async_update_if_not_in_progress,
            timedelta(seconds=float(1)),
        )


@pytest.mark.asyncio
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

    cast(Any, entity).async_run = MagicMock(name="async_run")
    with patch(
        "custom_components.modbus_local_gateway.coordinator"
        ".CoordinatorEntity.async_added_to_hass"
    ) as mock_super:
        mock_super.return_value = MagicMock()
        await entity.async_added_to_hass()
        mock_super.assert_called_once()
        cast(Any, entity).async_run.assert_called_once()


@pytest.mark.asyncio
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

    cast(Any, entity)._async_cancel_update_polling = MagicMock()
    cast(Any, entity)._async_cancel_future_pending_update = MagicMock()
    with patch(
        "custom_components.modbus_local_gateway.coordinator.CoordinatorEntity"
        ".async_will_remove_from_hass"
    ) as mock_super:
        await entity.async_will_remove_from_hass()
        cast(Any, entity)._async_cancel_update_polling.assert_called_once()
        cast(Any, entity)._async_cancel_future_pending_update.assert_called_once()
        mock_super.assert_called_once()


@pytest.mark.asyncio
async def test_async_update_entity(mock_config_entry: ConfigEntry) -> None:
    """Test async_update_entity calls _update_device."""
    hass = MagicMock()
    gateway = MagicMock()
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=mock_config_entry,
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

    cast(Any, coordinator)._update_device = AsyncMock()
    cast(Any, coordinator)._update_device.return_value = None
    await coordinator.async_update_entity(ctx1)
    cast(Any, coordinator)._update_device.assert_called_once()

    cast(Any, coordinator)._update_device.return_value = {"test1": "value1"}
    await coordinator.async_update_entity(ctx1)
    assert coordinator.data == {"test1": "value1"}

    cast(Any, coordinator)._update_device.return_value = {"test2": "value2"}
    await coordinator.async_update_entity(ctx2)
    assert coordinator.data == {"test1": "value1", "test2": "value2"}

    cast(Any, coordinator)._update_device.return_value = {"test2": "value3"}
    await coordinator.async_update_entity(ctx2)
    assert coordinator.data == {"test1": "value1", "test2": "value3"}


@pytest.mark.asyncio
async def test_an_entity_read_restores_coordinator_success(
    mock_config_entry: ConfigEntry,
) -> None:
    """A device that answers one entity again is no longer unavailable."""
    coordinator = _coordinator(mock_config_entry)
    coordinator.last_update_success = False
    coordinator.data = {}
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test1",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    cast(Any, coordinator)._update_device = AsyncMock(return_value={"test1": "value1"})

    await coordinator.async_update_entity(ctx)

    assert coordinator.last_update_success is True
    assert coordinator.data == {"test1": "value1"}


@pytest.mark.asyncio
async def test_a_failed_entity_read_leaves_coordinator_success_alone(
    mock_config_entry: ConfigEntry,
) -> None:
    """An entity that got nothing back does not claim the device answered."""
    coordinator = _coordinator(mock_config_entry)
    coordinator.last_update_success = False
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test1",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    cast(Any, coordinator)._update_device = AsyncMock(side_effect=UpdateFailed())

    await coordinator.async_update_entity(ctx)

    assert coordinator.last_update_success is False


@pytest.mark.asyncio
async def test_async_update_with_no_coordinator_entities(
    mock_config_entry: ConfigEntry,
) -> None:
    """A device config where EVERY entity sets scan_interval must not fail.

    async_update only polls entities without a scan_interval. If a config gives
    one to all of them that list is empty, and raising here would set
    last_update_success False and mark every entity unavailable - including the
    ones their own timers are polling perfectly well.
    """
    client = MagicMock()
    coordinator = ModbusCoordinator(
        hass=MagicMock(),
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=client,
        gateway="Test",
    )

    entities: list[ModbusContext] = [
        ModbusContext(
            1,
            ModbusSensorEntityDescription(
                register_address=1,
                key="own_timer",
                data_type=ModbusDataType.HOLDING_REGISTER,
                scan_interval=10,
            ),
        )
    ]
    # what the entity's own timer already stored, via async_update_entity
    coordinator.data = {"own_timer": 42}

    with patch(
        "custom_components.modbus_local_gateway.coordinator."
        "ModbusCoordinator.async_contexts",
        return_value=entities,
    ):
        result = await coordinator.async_update()

    assert result == {"own_timer": 42}  # existing data preserved, not wiped
    client.update_device.assert_not_called()  # nothing was polled


def _coordinator(mock_config_entry: ConfigEntry) -> ModbusCoordinator:
    """Build a coordinator with everything around it mocked."""
    return ModbusCoordinator(
        hass=MagicMock(),
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
    )


def test_is_unavailable_defaults_false(mock_config_entry: ConfigEntry) -> None:
    """An entity nothing has been said about is not unavailable."""
    coordinator = _coordinator(mock_config_entry)
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test_key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )

    assert coordinator.is_unavailable(ctx) is False


@pytest.mark.asyncio
async def test_async_update_entity_swallows_a_failed_poll(
    mock_config_entry: ConfigEntry,
) -> None:
    """A self-polling entity keeps its cached value when its own read fails."""
    coordinator = _coordinator(mock_config_entry)
    ctx = ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key="test_key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    coordinator.data = {"test_key": 42}

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})  # the device said nothing at all
    cast(Any, coordinator.client).update_device.return_value = future

    result = cast(Any, await coordinator.async_update_entity(ctx))
    assert result is None
    assert coordinator.data == {"test_key": 42}


def _single_entity_context(key: str = "test_key") -> ModbusContext:
    """One entity reading one input register."""
    return ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key=key,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )


@pytest.mark.asyncio
async def test_a_single_failed_read_keeps_the_last_value(
    mock_config_entry: ConfigEntry,
) -> None:
    """One missed read on an answering device is left on the value it had.

    A TCP-to-serial bridge answers a request after the client has stopped
    waiting for it, one register read is lost, and before this change every
    entity that missed went unavailable for a cycle even though the device was
    answering. The entity keeps its last value instead.
    """
    coordinator = _coordinator(mock_config_entry)
    coordinator.data = {"test_key": 42}
    ctx = _single_entity_context()

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future

    data = await coordinator._update_device([ctx])

    assert data == {"test_key": 42}
    assert coordinator.is_unavailable(ctx) is False


@pytest.mark.asyncio
async def test_a_second_consecutive_failed_read_goes_unavailable(
    mock_config_entry: ConfigEntry,
) -> None:
    """Two reads in a row that miss is not a blip, so the entity goes unavailable."""
    coordinator = _coordinator(mock_config_entry)
    coordinator.data = {"test_key": 42}
    ctx = _single_entity_context()

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future

    await coordinator._update_device([ctx])
    assert coordinator.is_unavailable(ctx) is False

    data = await coordinator._update_device([ctx])

    assert data == {}
    assert coordinator.is_unavailable(ctx) is True


@pytest.mark.asyncio
async def test_a_read_that_recovers_clears_the_tolerated_miss(
    mock_config_entry: ConfigEntry,
) -> None:
    """A good read ends the tolerance, so a later single miss is tolerated again."""
    coordinator = _coordinator(mock_config_entry)
    coordinator.data = {"test_key": 42}
    ctx = _single_entity_context()

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future

    await coordinator._update_device([ctx])
    assert coordinator.is_unavailable(ctx) is False

    future2: asyncio.Future[Any] = asyncio.Future()
    future2.set_result({"test_key": MagicMock()})
    cast(Any, coordinator.client).update_device.return_value = future2
    with patch(
        "custom_components.modbus_local_gateway.conversion"
        ".Conversion.convert_from_response",
        return_value=42,
    ):
        data = await coordinator._update_device([ctx])
    assert data["test_key"] == 42
    assert coordinator.is_unavailable(ctx) is False

    future3: asyncio.Future[Any] = asyncio.Future()
    future3.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future3

    data = await coordinator._update_device([ctx])

    assert data == {"test_key": 42}
    assert coordinator.is_unavailable(ctx) is False


@pytest.mark.asyncio
async def test_a_miss_with_nothing_kept_is_unavailable(
    mock_config_entry: ConfigEntry,
) -> None:
    """A read that never produced a value has nothing to stay on: unavailable.

    Only a value the entity already had can be kept; an entity that has never
    been read (or that is already unavailable) goes straight to unavailable.
    """
    coordinator = _coordinator(mock_config_entry)
    ctx = _single_entity_context()
    coordinator.data = {"other_key": 1}

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future

    data = await coordinator._update_device([ctx])

    assert data == {}
    assert coordinator.is_unavailable(ctx) is True


@pytest.mark.asyncio
async def test_unavailable_value_marks_entity_and_clears_again(
    mock_config_entry: ConfigEntry,
) -> None:
    """A rejected read marks the entity unavailable; a good read clears it.

    The key is also kept OUT of `data`, so every platform's existing
    `if value is not None` guard skips the update rather than publishing the
    sentinel as if it were a reading.
    """
    coordinator = _coordinator(mock_config_entry)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test_key",
        conv_unavailable_values=[255],
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({"test_key": MagicMock()})
    cast(Any, coordinator.client).update_device.return_value = future

    with patch(
        "custom_components.modbus_local_gateway.conversion"
        ".Conversion.convert_from_response",
        side_effect=ValueUnavailable(desc, 255, "declared in `unavailable_values`"),
    ):
        data = await coordinator._update_device([ctx])
    assert coordinator.is_unavailable(ctx) is True
    assert "test_key" not in data

    future2: asyncio.Future[Any] = asyncio.Future()
    future2.set_result({"test_key": MagicMock()})
    cast(Any, coordinator.client).update_device.return_value = future2
    with patch(
        "custom_components.modbus_local_gateway.conversion"
        ".Conversion.convert_from_response",
        return_value=42,
    ):
        data = await coordinator._update_device([ctx])
    assert coordinator.is_unavailable(ctx) is False
    assert data["test_key"] == 42


@pytest.mark.asyncio
async def test_all_unavailable_is_not_a_failed_refresh(
    mock_config_entry: ConfigEntry,
) -> None:
    """Every value being a declared sentinel is a sound poll, not a failure."""
    coordinator = _coordinator(mock_config_entry)
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test_key",
        conv_unavailable_values=[255],
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({"test_key": MagicMock()})
    cast(Any, coordinator.client).update_device.return_value = future

    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator"
            ".ModbusCoordinator.async_contexts",
            return_value=[ctx],
        ),
        patch(
            "custom_components.modbus_local_gateway.conversion"
            ".Conversion.convert_from_response",
            side_effect=ValueUnavailable(desc, 255, "declared in `unavailable_values`"),
        ),
    ):
        assert await coordinator.async_update() == {}
    assert coordinator.is_unavailable(ctx) is True


def test_entity_unavailable_for_declared_value(mock_config_entry: ConfigEntry) -> None:
    """The availability override covers every platform from the shared base."""
    coordinator = _coordinator(mock_config_entry)
    coordinator.last_update_success = True
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="test_key",
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc)
    entity = ModbusCoordinatorEntity(coordinator, ctx, DeviceInfo(identifiers=set()))
    entity._attr_available = True

    # Nothing read yet: there is no value behind the entity to report as available.
    assert entity.available is False

    coordinator._initial_poll_done = True
    assert entity.available is True

    coordinator._unavailable_keys.add("test_key")
    assert entity.available is False

    coordinator._unavailable_keys.discard("test_key")
    assert entity.available is True

    coordinator.last_update_success = False
    assert entity.available is False
