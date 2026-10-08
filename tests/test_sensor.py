"""Sensor tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
import pytest

from custom_components.modbus_local_gateway.const import (
    SUBENTRY_TYPE_DEVICE,
)
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management import modbus_device_info
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.sensor import (
    ModbusSensorEntity,
    async_setup_entry,
)

from .conftest import mock_gateway_entry, mock_runtime


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
    entry.runtime_data = mock_runtime({subentry_id: coordinator})

    pm1 = PropertyMock(
        return_value=[
            ModbusSensorEntityDescription(
                key="key1",
                register_address=1,
                data_type=ModbusDataType.INPUT_REGISTER,
            ),
            ModbusSensorEntityDescription(
                key="key2",
                register_address=2,
                data_type=ModbusDataType.HOLDING_REGISTER,
            ),
        ]
    )
    pm2 = PropertyMock(return_value="")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management."
            "modbus_device_info.load_yaml",
            return_value={"device": MagicMock()},
        ),
        patch.object(modbus_device_info.ModbusDeviceInfo, "entity_descriptions", pm1),
        patch.object(modbus_device_info.ModbusDeviceInfo, "manufacturer", pm2),
        patch.object(modbus_device_info.ModbusDeviceInfo, "model", pm2),
    ):
        coordinator.device_info = modbus_device_info.ModbusDeviceInfo("test.yaml")
        await async_setup_entry(hass, entry, callback.add)

        callback.add.assert_called_once()
        assert (
            len(callback.add.call_args[0][0]) == 2
        )  # Both input and holding registers
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
        ModbusEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    coordinator.get_data.return_value = None
    entity._handle_coordinator_update()

    coordinator.get_data.assert_called_once_with(ctx)
    cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_exception() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    ctx = ModbusContext(
        1,
        ModbusEntityDescription(
            register_address=1,
            key="key",
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.side_effect = Exception()
    cast(Any, entity).async_write_ha_state = MagicMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
    ):
        mocked_name.return_value = "Test"
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        debug.assert_not_called()
        warning.assert_not_called()
        error.assert_called_once()
        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_value() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = 1
    cast(Any, entity).async_write_ha_state = MagicMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
    ):
        mocked_name.return_value = "Test"
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_update_reset() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    coordinator.get_data.return_value = 1

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
        patch.object(entity, "state_class", new_callable=PropertyMock) as mocked_state,
        patch.object(
            entity, "last_reset", new_callable=PropertyMock
        ) as mocked_last_reset,
        patch.object(
            entity, "_attr_native_value", new_callable=PropertyMock
        ) as mocked_attr_native_value,
    ):
        mocked_name.return_value = "Test"
        mocked_state.return_value = SensorStateClass.TOTAL_INCREASING
        mocked_last_reset.return_value = None
        mocked_attr_native_value.return_value = 2

        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called_once()
        warning.assert_not_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()
        mocked_last_reset.assert_not_called()


@pytest.mark.asyncio
async def test_update_never_reset() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        never_resets=True,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    coordinator.get_data.return_value = 1
    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
        patch.object(
            entity, "last_reset", new_callable=PropertyMock
        ) as mocked_last_reset,
    ):
        mocked_name.return_value = "Test"
        mocked_last_reset.return_value = None
        entity._attr_native_value = 2
        entity.state_class = SensorStateClass.TOTAL_INCREASING
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        error.assert_not_called()
        debug.assert_called()
        warning.assert_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()
        mocked_last_reset.assert_not_called()


@pytest.mark.asyncio
async def test_update_deviceupdate_hw_version() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="hw_version",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc=desc,
    )
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    coordinator.get_data.return_value = 1
    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch("custom_components.modbus_local_gateway.sensor.dr.async_get") as dr,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
        patch.object(entity, "state_class", new_callable=PropertyMock) as mocked_state,
        patch.object(
            entity, "last_reset", new_callable=PropertyMock
        ) as mocked_last_reset,
        patch.object(
            entity, "_attr_native_value", new_callable=PropertyMock
        ) as mocked_attr_native_value,
    ):
        mocked_name.return_value = "Test"
        mocked_state.return_value = SensorStateClass.TOTAL_INCREASING
        mocked_last_reset.return_value = None
        mocked_attr_native_value.return_value = 2
        dr.return_value = MagicMock()

        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        dr.assert_called_once_with(entity.hass)
        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()
        mocked_last_reset.assert_not_called()


@pytest.mark.asyncio
async def test_update_deviceupdate_sw_version() -> None:
    """Test the coordinator update function"""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="sw_version",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc=desc,
    )
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    coordinator.get_data.return_value = 1
    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.error") as error,
        patch("custom_components.modbus_local_gateway.sensor.dr.async_get") as dr,
        patch.object(entity, "name", new_callable=PropertyMock) as mocked_name,
        patch.object(entity, "state_class", new_callable=PropertyMock) as mocked_state,
        patch.object(
            entity, "last_reset", new_callable=PropertyMock
        ) as mocked_last_reset,
        patch.object(
            entity, "_attr_native_value", new_callable=PropertyMock
        ) as mocked_attr_native_value,
    ):
        mocked_name.return_value = "Test"
        mocked_state.return_value = SensorStateClass.TOTAL_INCREASING
        mocked_last_reset.return_value = None
        mocked_attr_native_value.return_value = 2
        dr.return_value = MagicMock()

        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)

        dr.assert_called_once_with(entity.hass)
        error.assert_not_called()
        debug.assert_called()
        warning.assert_not_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()
        mocked_last_reset.assert_not_called()


@pytest.mark.asyncio
async def test_update_device_version_lookup_is_scoped_to_the_config_entry() -> None:
    """Version lookups use the entry-scoped API, not the deprecated one.

    Identifiers are no longer unique across config entries, so the device that
    belongs to this entry is selected by its entry id, and a device that happens
    to share identifiers from another entry is not picked up instead. The
    deprecated `async_get_device` is not invoked.
    """
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry-1"
    desc = ModbusSensorEntityDescription(
        key="hw_version",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc=desc)
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    found = MagicMock()
    found.id = "device-1"
    registry = MagicMock()
    registry.async_get_device_by_identifier.return_value = found
    registry.async_get_device = MagicMock()

    with patch(
        "custom_components.modbus_local_gateway.sensor.dr.async_get",
        return_value=registry,
    ):
        entity._update_device_versions("1.2.3")

    registry.async_get_device_by_identifier.assert_called_once_with(
        ("a", "b"), "entry-1"
    )
    registry.async_get_device.assert_not_called()
    registry.async_update_device.assert_called_once_with(
        device_id="device-1",
        hw_version="1.2.3",
    )


@pytest.mark.asyncio
async def test_update_device_version_missing_device_is_handled() -> None:
    """A device not found updates nothing and raises nothing."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry-1"
    desc = ModbusSensorEntityDescription(
        key="sw_version",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc=desc)
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    registry = MagicMock()
    registry.async_get_device_by_identifier.return_value = None

    with patch(
        "custom_components.modbus_local_gateway.sensor.dr.async_get",
        return_value=registry,
    ):
        entity._update_device_versions("1.2.3")

    registry.async_get_device_by_identifier.assert_called_once_with(
        ("a", "b"), "entry-1"
    )
    registry.async_update_device.assert_not_called()


@pytest.mark.asyncio
async def test_update_device_version_without_config_entry_is_handled() -> None:
    """A coordinator with no config entry skips the lookup without error."""
    coordinator = MagicMock()
    coordinator.config_entry = None
    desc = ModbusSensorEntityDescription(
        key="hw_version",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(1, desc=desc)
    device: DeviceInfo = {"identifiers": {("a", "b")}}
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)

    registry = MagicMock()

    with patch(
        "custom_components.modbus_local_gateway.sensor.dr.async_get",
        return_value=registry,
    ):
        entity._update_device_versions("1.2.3")

    registry.async_get_device_by_identifier.assert_not_called()
    registry.async_update_device.assert_not_called()


@pytest.mark.asyncio
async def test_handle_coordinator_update_ignore_same_value() -> None:
    """Test _handle_coordinator_update ignores the same value."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc=desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = 10
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
    ):
        entity._attr_native_value = 10

        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        debug.assert_called_once_with(
            "Ignoring device value for %s: %s – same as previous value",
            "key",
            10,
        )

        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_coordinator_update_ignore_large_change() -> None:
    """Test _handle_coordinator_update ignores large changes."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        max_change=5,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    entity._first_update_received = True
    coordinator.get_data.return_value = 20
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
    ):
        entity._attr_native_value = 10
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        warning.assert_called_once_with(
            ("Ignoring device value for %s: %s – change Δ=%s exceeds max_change=%s"),
            "key",
            20,
            10,
            5,
        )

        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_coordinator_update_allow_large_change_on_initial() -> None:
    """Test _handle_coordinator_update allows large changes on initial update."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        max_change=5,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    entity._attr_native_value = 10
    entity._first_update_received = False
    coordinator.get_data.return_value = 20
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning",
        ) as warning,
    ):
        entity._handle_coordinator_update()
        coordinator.get_data.assert_called_once_with(ctx)
        warning.assert_not_called()
        assert entity._first_update_received
        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_coordinator_update_update_value() -> None:
    """Test _handle_coordinator_update updates the value."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = 15
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch.object(
            entity, "_attr_native_value", new_callable=PropertyMock
        ) as mocked_attr_native_value,
    ):
        mocked_attr_native_value.return_value = 10
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        cast(Any, entity).async_write_ha_state.assert_called_once()
        debug.assert_called_with(
            "Updating device with %s as %s",
            "key",
            15,
        )


@pytest.mark.asyncio
async def test_handle_coordinator_update_update_smaller_value() -> None:
    """Test _handle_coordinator_update updates the value if smaller."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="key",
        data_type=ModbusDataType.INPUT_REGISTER,
        max_change=5,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = 15
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
        patch.object(
            entity, "_attr_native_value", new_callable=PropertyMock
        ) as mocked_attr_native_value,
    ):
        mocked_attr_native_value.return_value = 100
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        cast(Any, entity).async_write_ha_state.assert_called_once()
        debug.assert_called_with(
            "Updating device with %s as %s",
            "key",
            15,
        )


@pytest.mark.asyncio
async def test_handle_coordinator_update_smaller_than_precision() -> None:
    """Test _handle_coordinator_update updates the value if smaller."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        register_address=1,
        key="key",
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=2,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    coordinator.get_data.return_value = 100.0015
    cast(Any, entity).async_write_ha_state = MagicMock()
    with (
        patch("custom_components.modbus_local_gateway.sensor._LOGGER.debug") as debug,
    ):
        entity._attr_native_value = 100.001
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        cast(Any, entity).async_write_ha_state.assert_called_once()
        debug.assert_called_with(
            "Ignoring device value for %s: %s – same as previous value",
            "key",
            100.0015,
        )


@pytest.mark.asyncio
async def test_handle_coordinator_update_never_resets() -> None:
    """Test _handle_coordinator_update ignores decreasing values for never resets."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        never_resets=True,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()
    coordinator.get_data.return_value = 10

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
    ):
        entity._attr_native_value = 15
        entity.state_class = SensorStateClass.TOTAL_INCREASING
        entity._handle_coordinator_update()

        coordinator.get_data.assert_called_once_with(ctx)
        warning.assert_called_once_with(
            "Ignoring device value with %s as %s - never resets %s",
            "key",
            10,
            15,
        )

        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_coordinator_update_never_resets_tolerates_rounding_dip() -> None:
    """Test rounding dips within multiplier don't trigger never_resets warning."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="Eload_total",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        never_resets=True,
        conv_multiplier=0.1,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()
    coordinator.get_data.return_value = 41579.9  # 0.1 less than current

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
    ):
        entity._attr_native_value = 41580.0
        entity.state_class = SensorStateClass.TOTAL_INCREASING
        entity._handle_coordinator_update()

        warning.assert_not_called()
        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_handle_coordinator_update_never_resets_still_warns_on_real_drop() -> (
    None
):
    """Test real drops beyond multiplier still warn."""
    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="Eload_total",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        never_resets=True,
        conv_multiplier=0.1,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()
    coordinator.get_data.return_value = 41579.0  # 1.0 drop > 0.1

    with (
        patch(
            "custom_components.modbus_local_gateway.sensor._LOGGER.warning"
        ) as warning,
    ):
        entity._attr_native_value = 41580.0
        entity.state_class = SensorStateClass.TOTAL_INCREASING
        entity._handle_coordinator_update()

        warning.assert_called_once()
        cast(Any, entity).async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_native_value_rounds_float_with_precision() -> None:
    """Test native_value rounds float with precision."""

    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=2,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    entity._attr_native_value = 12.3456
    result = entity.native_value
    assert result == pytest.approx(12.35)


@pytest.mark.asyncio
async def test_native_value_returns_non_float() -> None:
    """Test native_value returns non-float values unchanged."""

    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=2,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    entity._attr_native_value = 42
    result = entity.native_value
    assert result == 42


@pytest.mark.asyncio
async def test_native_value_no_precision() -> None:
    """Test native_value returns float unchanged if no precision."""

    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=None,  # No precision set
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    entity._attr_native_value = 12.3456
    result = entity.native_value
    assert result == pytest.approx(12.3456)


@pytest.mark.asyncio
async def test_native_value_none_result() -> None:
    """Test native_value returns None if result is None."""

    coordinator = MagicMock()
    desc = ModbusSensorEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=2,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    entity._attr_native_value = None
    result = entity.native_value
    assert result is None


@pytest.mark.asyncio
async def test_native_value_non_modbus_description() -> None:
    """Test native_value for non-ModbusSensorEntityDescription descriptions."""

    coordinator = MagicMock()
    desc = ModbusEntityDescription(
        key="key",
        register_address=1,
        data_type=ModbusDataType.INPUT_REGISTER,
        precision=2,
    )
    ctx = ModbusContext(
        1,
        desc,
    )
    device = MagicMock()
    entity = ModbusSensorEntity(coordinator=coordinator, ctx=ctx, device=device)
    cast(Any, entity).async_write_ha_state = MagicMock()

    entity._attr_native_value = 12.3456
    result = entity.native_value
    assert result == pytest.approx(12.3456)
