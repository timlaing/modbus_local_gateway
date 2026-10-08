"""The first read of a device: deferred past startup, one read per device."""

# pylint: disable=unexpected-keyword-arg, protected-access
import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pymodbus.pdu.pdu import ModbusPDU
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.coordinator import ModbusCoordinator
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.exceptions import ModbusNoResponseError
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
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


_CONVERT_FROM_RESPONSE = (
    "custom_components.modbus_local_gateway.conversion.Conversion.convert_from_response"
)


def _reads(entities: list[ModbusContext], **_: Any) -> dict[str, Any]:
    """A read that answers every entity it was asked about."""
    return {ctx.desc.key: MagicMock() for ctx in entities}


def _never_ends() -> Any:
    """Return a read that only ends when the test ends."""

    async def _read(*_: Any, **__: Any) -> dict[str, Any]:
        await asyncio.Event().wait()
        return {}

    return _read


def _entity(
    key: str, scan_interval: int | None = None, device_id: int = 1
) -> ModbusContext:
    """A one-register entity for the polling tests."""
    return ModbusContext(
        device_id,
        ModbusSensorEntityDescription(
            register_address=1,
            key=key,
            data_type=ModbusDataType.INPUT_REGISTER,
            scan_interval=scan_interval,
        ),
    )


def _starting_coordinator(
    hass: HomeAssistant, entities: list[ModbusContext]
) -> ModbusCoordinator:
    """A coordinator of a gateway whose client answers nothing but slowly."""
    coordinator = ModbusCoordinator(
        hass=hass,
        config_entry=MockConfigEntry(domain=DOMAIN, data={}),
        gateway_device=MagicMock(),
        client=AsyncMock(spec=AsyncModbusTcpClientGateway),
        gateway="Test",
    )
    coordinator.async_contexts = MagicMock(return_value=entities)  # type: ignore[method-assign]
    return coordinator


async def _drain(hass: HomeAssistant) -> None:
    """Let the background initial poll run to completion."""
    for _ in range(20):
        await asyncio.sleep(0)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_the_first_poll_waits_for_startup(hass: HomeAssistant) -> None:
    """Nothing is read while Home Assistant is still starting.

    Reading a device that is not answering costs a timeout sequence, and Home
    Assistant waits for the work that setup starts.
    """
    hass.set_state(CoreState.starting)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])
    cast(Any, coordinator.client).update_device.return_value = {}

    coordinator.async_schedule_initial_poll()
    await hass.async_block_till_done()

    cast(Any, coordinator.client).update_device.assert_not_called()
    assert coordinator.initial_poll_done is False

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await _drain(hass)

    cast(Any, coordinator.client).update_device.assert_awaited_once()
    assert coordinator.initial_poll_done is True


@pytest.mark.asyncio
async def test_the_first_poll_runs_at_once_when_home_assistant_is_up(
    hass: HomeAssistant,
) -> None:
    """A reload happens while Home Assistant runs, so there is nothing to wait for."""
    hass.set_state(CoreState.running)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])
    cast(Any, coordinator.client).update_device.return_value = {}

    coordinator.async_schedule_initial_poll()
    await _drain(hass)

    cast(Any, coordinator.client).update_device.assert_awaited_once()
    assert coordinator.initial_poll_done is True


@pytest.mark.asyncio
async def test_the_first_poll_happens_once(hass: HomeAssistant) -> None:
    """Scheduling again does not read the device a second time."""
    hass.set_state(CoreState.running)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])
    cast(Any, coordinator.client).update_device.return_value = {}

    coordinator.async_schedule_initial_poll()
    coordinator.async_schedule_initial_poll()
    await _drain(hass)

    cast(Any, coordinator.client).update_device.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_first_poll_covers_self_polling_entities(hass: HomeAssistant) -> None:
    """An entity with its own scan_interval is read now, not at its first tick."""
    hass.set_state(CoreState.running)
    slow = _entity("slow", scan_interval=300)
    shared = _entity("shared")
    coordinator = _starting_coordinator(hass, [slow, shared])
    cast(Any, coordinator.client).update_device.side_effect = _reads

    with patch(_CONVERT_FROM_RESPONSE, return_value=42):
        coordinator.async_schedule_initial_poll()
        await _drain(hass)

        (read_entities,) = cast(Any, coordinator.client).update_device.call_args.args
        assert [ctx.desc.key for ctx in read_entities] == ["slow", "shared"]

        # The next refresh leaves the self-polling entity to its own timer.
        await coordinator.async_update()

    (read_entities,) = cast(Any, coordinator.client).update_device.call_args.args
    assert [ctx.desc.key for ctx in read_entities] == ["shared"]


@pytest.mark.asyncio
async def test_a_second_refresh_does_not_queue_another_poll(
    hass: HomeAssistant,
) -> None:
    """A refresh that arrives mid-poll is answered from the one in flight."""
    hass.set_state(CoreState.running)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])
    release = asyncio.Event()

    async def _slow_read(entities: list[ModbusContext], **_: Any) -> dict[str, Any]:
        await release.wait()
        return _reads(entities)

    cast(Any, coordinator.client).update_device.side_effect = _slow_read

    with patch(_CONVERT_FROM_RESPONSE, return_value=42):
        poll = asyncio.create_task(coordinator.async_update())
        await asyncio.sleep(0)
        await coordinator.async_update()
        release.set()
        await poll

    cast(Any, coordinator.client).update_device.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_pending_first_poll_is_dropped_on_unload(hass: HomeAssistant) -> None:
    """Unloading the entry leaves nothing waiting to read the device."""
    hass.set_state(CoreState.starting)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])

    coordinator.async_schedule_initial_poll()
    coordinator.async_cancel_initial_poll()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    cast(Any, coordinator.client).update_device.assert_not_called()


@pytest.mark.asyncio
async def test_a_cancelled_first_poll_leaves_no_task_behind(
    hass: HomeAssistant,
) -> None:
    """A poll that was already running is cancelled rather than left to finish."""
    hass.set_state(CoreState.running)
    coordinator = _starting_coordinator(hass, [_entity("test_key")])
    started = asyncio.Event()
    release = asyncio.Event()

    async def _hang(*_: Any, **__: Any) -> dict[str, Any]:
        started.set()
        await release.wait()
        return {}

    cast(Any, coordinator.client).update_device.side_effect = _hang

    coordinator.async_schedule_initial_poll()
    await started.wait()
    coordinator.async_cancel_initial_poll()
    await hass.async_block_till_done()

    assert coordinator._initial_poll_task is None


@pytest.mark.asyncio
async def test_a_hundred_entities_behind_one_silent_device_cost_one_read(
    hass: HomeAssistant,
) -> None:
    """The reported case: 112 entities, one device that never answers.

    Reading each entity separately meant one timeout sequence per entity while
    Home Assistant waited for the whole lot.
    """
    hass.set_state(CoreState.starting)
    entities = [_entity(f"key_{number}") for number in range(112)]
    coordinator = _starting_coordinator(hass, entities)
    read_count = 0

    async def _silent(*_: Any, **__: Any) -> dict[str, Any]:
        nonlocal read_count
        read_count += 1
        raise ModbusNoResponseError("no answer", partial={})

    cast(Any, coordinator.client).update_device.side_effect = _silent

    coordinator.async_schedule_initial_poll()
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await _drain(hass)

    assert read_count == 1
    assert coordinator.initial_poll_done is True


@pytest.mark.asyncio
async def test_a_device_that_stops_answering_keeps_what_it_sent(
    mock_config_entry: ConfigEntry,
) -> None:
    """Values read before the silence are kept, the rest become unavailable."""
    coordinator = _coordinator(mock_config_entry)
    got_a_value = _entity("first")
    went_quiet = _entity("second")
    never_asked = _entity("third")

    future: asyncio.Future[Any] = asyncio.Future()
    future.set_result({})
    cast(Any, coordinator.client).update_device.return_value = future

    partial: dict[str, ModbusPDU] = {"first": cast(ModbusPDU, MagicMock())}
    cast(Any, coordinator.client).update_device = AsyncMock(
        side_effect=ModbusNoResponseError("went quiet", partial=partial)
    )
    with patch(
        "custom_components.modbus_local_gateway.conversion"
        ".Conversion.convert_from_response",
        return_value=42,
    ):
        data = await coordinator._update_device([got_a_value, went_quiet, never_asked])

    assert data == {"first": 42}
    assert coordinator.is_unavailable(got_a_value) is False
    assert coordinator.is_unavailable(went_quiet) is True
    assert coordinator.is_unavailable(never_asked) is True


@pytest.mark.asyncio
async def test_a_poll_that_never_finishes_fails(
    mock_config_entry: ConfigEntry,
) -> None:
    """A poll stuck behind the shared lock is given up on, not waited for forever."""
    coordinator = _coordinator(mock_config_entry)
    cast(Any, coordinator.client).update_device.side_effect = _never_ends()

    entity = _entity("test_key")
    with (
        patch(
            "custom_components.modbus_local_gateway.coordinator._POLL_BACKSTOP", 0.01
        ),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._update_device([entity])
