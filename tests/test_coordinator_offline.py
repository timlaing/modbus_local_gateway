"""What a device that is not answering means for its entities."""

# pylint: disable=protected-access, unexpected-keyword-arg
from typing import Any, cast
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
import pytest

from custom_components.modbus_local_gateway.const import OPTIONS_EXPECTED_OFFLINE
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
from custom_components.modbus_local_gateway.tcp_client import DevicePolicy

_CONVERT_FROM_RESPONSE = (
    "custom_components.modbus_local_gateway.conversion.Conversion.convert_from_response"
)


class _Client:
    """A client that answers what it is told to.

    What is known about a device that has stopped answering belongs to the client,
    because that is where every way of asking a device for a value arrives. This
    stands in for it, saying only what the coordinator should act on.
    """

    def __init__(self) -> None:
        """A device that has answered everything so far."""
        self.online: dict[int, bool] = {}
        self.answers: Any = None
        self.policies: list[DevicePolicy] = []
        self.polled: list[list[ModbusContext]] = []

    async def update_device(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Answer with whatever this test set up, remembering how it was asked."""
        self.policies.append(kwargs["policy"])
        self.polled.append(args[0])
        assert self.answers is not None
        answered = await cast(Any, self.answers)(*args, **kwargs)
        return cast(dict[str, Any], answered)

    def device_online(self, device_id: int) -> bool:
        """Whether the device answered its last read."""
        return self.online.get(device_id, True)


def _coordinator(
    mock_config_entry: ConfigEntry, client: _Client | None = None
) -> ModbusCoordinator:
    """Build a coordinator with everything around it mocked."""
    coordinator = ModbusCoordinator(
        hass=MagicMock(),
        config_entry=mock_config_entry,
        gateway_device=MagicMock(),
        client=cast(Any, client or _Client()),
        gateway="Test",
    )
    coordinator._device_id = 1
    return coordinator


def _entity(key: str = "test_key", scan_interval: int | None = None) -> ModbusContext:
    """A one-register entity, polling on its own timer if it is given one."""
    return ModbusContext(
        1,
        ModbusSensorEntityDescription(
            register_address=1,
            key=key,
            data_type=ModbusDataType.INPUT_REGISTER,
            scan_interval=scan_interval,
        ),
    )


def _keys(polls: list[list[ModbusContext]]) -> list[list[str]]:
    """What each read of this client was asked for."""
    return [[ctx.desc.key for ctx in poll] for poll in polls]


def _silent(*_: Any, **__: Any) -> Any:
    """A read that never gets an answer, as the client reports it."""

    async def _read(*__: Any, **___: Any) -> dict[str, Any]:
        raise ModbusNoResponseError("stopped answering", partial={})

    return _read


def _returns(data: dict[str, Any]) -> Any:
    """A read that came back with what it had to say."""

    async def _read(*_: Any, **__: Any) -> dict[str, Any]:
        return data

    return _read


def _partial(*answered: ModbusContext) -> Any:
    """A read that went quiet part way through, keeping what it had read."""

    async def _read(*_: Any, **__: Any) -> ModbusNoResponseError:
        raise ModbusNoResponseError(
            "stopped answering",
            partial={ctx.desc.key: MagicMock() for ctx in answered},
        )

    return _read


@pytest.mark.asyncio
async def test_a_device_that_is_off_is_not_a_failed_refresh(
    mock_config_entry: ConfigEntry,
) -> None:
    """A device that is off is a state, not a failure of the refresh.

    Home Assistant logs its own error for a failed refresh and stops reporting the
    coordinator as up to date, both of which say the same thing again on every
    cycle and neither of which tells the user anything the client has not.
    """
    client = _Client()
    client.answers = _silent()
    coordinator = _coordinator(mock_config_entry, client)
    coordinator.async_contexts = MagicMock(return_value=[_entity()])  # type: ignore[method-assign]

    assert await coordinator.async_update() == {}
    assert coordinator.last_update_success is True


@pytest.mark.asyncio
async def test_a_device_that_answers_part_of_a_poll_keeps_what_it_answered(
    mock_config_entry: ConfigEntry,
) -> None:
    """The values that came back stay; only the ones that did not go unavailable.

    A device that answers 3 of 5 is on the bus, and hiding the 3 behind the 2 that
    did not answer would be reporting less than the device just told us.
    """
    client = _Client()
    answered, silent_ctx = _entity("answered"), _entity("silent")
    client.answers = _partial(answered)
    coordinator = _coordinator(mock_config_entry, client)

    with _patch_convert():
        assert set(await coordinator._update_device([answered, silent_ctx])) == {
            "answered"
        }

    assert coordinator.is_unavailable(answered) is False
    assert coordinator.is_unavailable(silent_ctx) is True


@pytest.mark.asyncio
async def test_a_poll_the_gateway_never_answers_speaks_for_no_device(
    mock_config_entry: ConfigEntry,
) -> None:
    """A gateway that will not connect is the gateway's line to say, not a device's.

    The client returns nothing and raises nothing, which is what an unreachable
    gateway looks like from here: no device read was answered, so no device has
    started answering.
    """
    client = _Client()
    client.answers = _returns({})
    coordinator = _coordinator(mock_config_entry, client)

    assert await coordinator._update_device([_entity()]) == {}
    assert coordinator.is_unavailable(_entity()) is True


def test_availability_follows_what_the_client_knows(
    mock_config_entry: ConfigEntry,
) -> None:
    """The client is asked, so a recovery probe is reflected without a poll.

    The probe runs inside the client's own poll, so the device can be known to be
    back between two polls of this coordinator: its entities have to become
    available when the client says so, not when the coordinator next reads.
    """
    client = _Client()
    coordinator = _coordinator(mock_config_entry, client)
    coordinator._initial_poll_done = True
    ctx = _entity()
    entity = ModbusCoordinatorEntity(coordinator, ctx, DeviceInfo(identifiers=set()))
    entity._attr_available = True

    assert entity.available is True

    client.online[1] = False
    assert entity.available is False

    client.online[1] = True
    assert entity.available is True


@pytest.mark.asyncio
async def test_an_entity_that_times_out_alone_is_not_the_device_going_away(
    mock_config_entry: ConfigEntry,
) -> None:
    """One register read on its own timer that gets nothing back is its own problem.

    The device is still answering everything else, so its other entities stay
    available: only a poll that asked the whole device can say the device has
    gone, and taking a whole device off the bus over one register would do exactly
    that to every entity that was not the one that timed out.
    """
    client = _Client()
    client.answers = _silent()
    coordinator = _coordinator(mock_config_entry, client)
    silent, other = _entity("silent"), _entity("other")

    with _patch_convert():
        assert await coordinator._update_device([silent], whole_device=False) == {}

    assert coordinator.is_unavailable(silent) is True
    assert coordinator.is_unavailable(other) is False


def _patch_convert() -> Any:
    """Let every read through the conversion, which is not what is under test here."""
    return patch(_CONVERT_FROM_RESPONSE, return_value=42)


@pytest.mark.asyncio
async def test_an_entity_is_not_read_while_its_device_is_not_answering(
    mock_config_entry: ConfigEntry,
) -> None:
    """An entity on its own timer does not read a device that has gone.

    A device that is off is asked by the refresh of the whole device and by
    nothing else: one read per entity per timer is how a device that is off for
    the night fills the bus and the log, and one of those reads on its own says
    nothing about whether the device is back.
    """
    client = _Client()
    client.answers = _returns({"own_timer": 42})
    coordinator = _coordinator(mock_config_entry, client)
    ctx = _entity("own_timer", scan_interval=10)
    client.online[1] = False

    with _patch_convert():
        await coordinator.async_update_entity(ctx)
    assert not client.polled

    # Once the device is answering, its entities read again on their own timers.
    client.online[1] = True
    with _patch_convert():
        await coordinator.async_update_entity(ctx)

    assert _keys(client.polled) == [["own_timer"]]
    assert coordinator.data == {"own_timer": 42}


@pytest.mark.asyncio
async def test_the_refresh_of_a_device_that_is_away_covers_the_whole_device(
    mock_config_entry: ConfigEntry,
) -> None:
    """A device whose entities all poll on their own timers is still found back.

    Those timers are not reading while it is away, so if the refresh left their
    entities out there would be nothing left to ask it with: it would be found
    out to be back by nobody, for as long as it was away.
    """
    client = _Client()
    client.answers = _returns({})
    coordinator = _coordinator(mock_config_entry, client)
    shared, own_timer = _entity("shared"), _entity("own_timer", scan_interval=10)
    coordinator.async_contexts = MagicMock(  # type: ignore[method-assign]
        return_value=[shared, own_timer]
    )
    client.online[1] = False

    await coordinator.async_update()
    assert _keys(client.polled) == [["shared", "own_timer"]]

    # And it is asked as it always was once it is answering: the entities with
    # their own timer are left to their own timer.
    client.online[1] = True
    client.polled.clear()
    await coordinator.async_update()
    assert _keys(client.polled) == [["shared"]]


@pytest.mark.asyncio
async def test_a_poll_carries_what_the_device_configured(
    mock_config_entry: ConfigEntry,
) -> None:
    """The client is told how this device wants to be polled.

    What a recovery probe reads and whether a device is expected to be quiet are
    settings of one device, not of the gateway it happens to be behind, so they
    travel with each poll rather than being remembered per gateway.
    """
    client = _Client()
    client.answers = _returns({})
    coordinator = _coordinator(mock_config_entry, client)
    coordinator._device_info = MagicMock(probe_key="status")
    coordinator._subentry_data = {OPTIONS_EXPECTED_OFFLINE: True}

    await coordinator._update_device([_entity()])
    assert client.policies == [
        DevicePolicy(whole_device=True, probe_key="status", expected_offline=True)
    ]

    # A read of one entity on its own timer is not asked about the whole device,
    # so it does not name a probe entity it has no intention of reading, and a
    # device that does not answer it is not put on a backoff over one register.
    await coordinator._update_device([_entity()], whole_device=False)
    assert client.policies[-1] == DevicePolicy(
        whole_device=False, probe_key=None, expected_offline=True
    )


@pytest.mark.asyncio
async def test_a_device_that_names_no_probe_is_polled_as_it_always_was(
    mock_config_entry: ConfigEntry,
) -> None:
    """Most devices have nothing to say about how to probe them."""
    client = _Client()
    client.answers = _returns({})
    coordinator = _coordinator(mock_config_entry, client)
    coordinator._device_info = MagicMock(probe_key=None)
    coordinator._subentry_data = {}

    await coordinator._update_device([_entity()])

    assert client.policies == [DevicePolicy()]
