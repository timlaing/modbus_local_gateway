"""What a device that is not answering says, and how often it says it."""

# pylint: disable=unexpected-keyword-arg, protected-access
import logging
from typing import Any, cast
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
import pytest

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import (
    ModbusCoordinator,
    ModbusCoordinatorEntity,
)
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.exceptions import ModbusNoResponseError

_LOGGER_NAME = "custom_components.modbus_local_gateway.coordinator"
_CONVERT_FROM_RESPONSE = (
    "custom_components.modbus_local_gateway.conversion.Conversion.convert_from_response"
)


def _coordinator(mock_config_entry: ConfigEntry) -> ModbusCoordinator:
    """Build a coordinator with everything around it mocked."""
    return ModbusCoordinator(
        hass=MagicMock(),
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=MagicMock(),
        gateway="Test",
    )


def _entity(key: str = "test_key") -> ModbusContext:
    """A one-register entity."""
    return ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key=key,
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
    )


def _answers(key: str = "test_key") -> Any:
    """A read that answers the one entity it was asked about."""

    async def _read(*_: Any, **__: Any) -> dict[str, Any]:
        return {key: MagicMock()}

    return _read


def _silent(*_: Any, **__: Any) -> Any:
    """A read that never gets an answer, as the client reports it."""

    async def _read(*__: Any, **___: Any) -> dict[str, Any]:
        raise ModbusNoResponseError("stopped answering", partial={})

    return _read


@pytest.mark.asyncio
async def test_a_device_that_goes_offline_is_reported_once(
    mock_config_entry: ConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """One info line when it goes, then silence for as long as it stays away.

    A device that is off is asked again on every cycle and none of those cycles
    has anything new to say, so a line per cycle is a line every few seconds for
    as long as the device is off.
    """
    coordinator = _coordinator(mock_config_entry)
    ctx = _entity()
    cast(Any, coordinator.client).update_device.side_effect = _silent()

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        for _ in range(5):
            await coordinator._update_device([ctx])

    assert caplog.text.count("stopped answering") == 1
    assert coordinator.device_online is False
    assert coordinator.is_unavailable(ctx) is True
    assert [r.levelno for r in caplog.records] == [logging.INFO]


@pytest.mark.asyncio
async def test_an_offline_device_is_not_a_failed_refresh(
    mock_config_entry: ConfigEntry,
) -> None:
    """A device that is off is a state, not a failure of the refresh.

    Home Assistant logs its own error for a failed refresh and stops reporting the
    coordinator as up to date, both of which say the same thing again on every
    cycle and neither of which tells the user anything the log does not.
    """
    coordinator = _coordinator(mock_config_entry)
    cast(Any, coordinator.client).update_device.side_effect = _silent()
    coordinator.async_contexts = MagicMock(  # type: ignore[method-assign]
        return_value=[_entity()]
    )

    assert await coordinator.async_update() == {}
    assert coordinator.last_update_success is True


@pytest.mark.asyncio
async def test_a_device_that_comes_back_is_reported_with_the_gap(
    mock_config_entry: ConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Recovery is the line worth having, and it says how long the device was gone."""
    coordinator = _coordinator(mock_config_entry)
    ctx = _entity()
    cast(Any, coordinator.client).update_device.side_effect = _silent()
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        await coordinator._update_device([ctx])

    cast(Any, coordinator.client).update_device.side_effect = _answers()
    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        patch(_CONVERT_FROM_RESPONSE, return_value=42),
    ):
        await coordinator._update_device([ctx])

    assert caplog.text.count("is answering again") == 1
    assert "silent for" in caplog.text
    assert coordinator.device_online is True
    assert coordinator.is_unavailable(ctx) is False


@pytest.mark.asyncio
async def test_going_offline_again_is_reported_again(
    mock_config_entry: ConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """The report is per change of state, so the next outage gets its own line."""
    coordinator = _coordinator(mock_config_entry)
    cast(Any, coordinator.client).update_device.side_effect = _silent()
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        await coordinator._update_device([_entity()])

    cast(Any, coordinator.client).update_device.side_effect = _answers()
    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        patch(_CONVERT_FROM_RESPONSE, return_value=42),
    ):
        await coordinator._update_device([_entity()])

    caplog.clear()
    cast(Any, coordinator.client).update_device.side_effect = _silent()
    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        await coordinator._update_device([_entity()])

    assert caplog.text.count("stopped answering") == 1


@pytest.mark.asyncio
async def test_a_device_with_nothing_to_read_is_not_reported_offline(
    mock_config_entry: ConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """A device config that declares nothing has not gone offline."""
    coordinator = _coordinator(mock_config_entry)

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        assert await coordinator._update_device([]) == {}

    assert caplog.text == ""


def test_entities_are_unavailable_while_the_device_is_silent(
    mock_config_entry: ConfigEntry,
) -> None:
    """Availability follows the state, without a failed refresh to carry it."""
    coordinator = _coordinator(mock_config_entry)
    coordinator._initial_poll_done = True
    ctx = _entity()
    entity = ModbusCoordinatorEntity(coordinator, ctx, DeviceInfo(identifiers=set()))
    entity._attr_available = True

    assert entity.available is True

    coordinator._device_online = False
    assert entity.available is False

    coordinator._device_online = True
    assert entity.available is True


_LOGGER_NAME = "custom_components.modbus_local_gateway.coordinator"
