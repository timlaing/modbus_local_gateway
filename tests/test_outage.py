"""What happens to a device that has stopped answering, and while it is away."""

# pylint: disable=protected-access, unexpected-keyword-arg
import asyncio
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pymodbus.framer import FramerType
from pymodbus.pdu.pdu import ModbusPDU
import pytest

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.exceptions import ModbusNoResponseError
from custom_components.modbus_local_gateway.tcp_client import (
    _PROBE_BACKOFF,
    AsyncModbusTcpClientGateway,
    DevicePolicy,
)

_LOGGER_NAME = "custom_components.modbus_local_gateway.tcp_client"
_MODULE = "custom_components.modbus_local_gateway.tcp_client"


class _Clock:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        """Start at zero, so every deadline in the code is a readable number."""
        self.now: float = 0.0

    def __call__(self) -> float:
        """The current time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the clock on."""
        self.now += seconds


class _AnswersEverything:
    """Marks a device that answers whatever it is asked."""


_ANSWERS_EVERYTHING = _AnswersEverything()


class _Device:
    """One device behind the gateway, and what it does when it is asked."""

    def __init__(
        self,
        device_id: int = 1,
        keys: tuple[str, ...] = ("first", "second"),
        answers: Any = _ANSWERS_EVERYTHING,
        stops_after: int | None = None,
    ) -> None:
        """A device that answers everything it is asked."""
        self.device_id = device_id
        self.entities = [
            ModbusContext(
                device_id,
                ModbusSensorEntityDescription(
                    register_address=index + 1,
                    key=key,
                    data_type=ModbusDataType.HOLDING_REGISTER,
                ),
            )
            for index, key in enumerate(keys)
        ]
        # None means the device does not answer at all; a dict of keys means it
        # answers those and is quiet about the rest.
        self.answers: dict[str, ModbusPDU] | None = (
            None
            if answers is None
            else (
                {entity.desc.key: MagicMock(spec=ModbusPDU) for entity in self.entities}
                if answers is _ANSWERS_EVERYTHING
                else answers
            )
        )
        # How many of a poll's reads it answers before going quiet mid-poll.
        self.stops_after = stops_after
        self.answered = 0
        # What it was asked for, so a test can tell a probe from a poll.
        self.read: list[str] = []

    async def process(
        self, entity: ModbusContext, data: dict[str, ModbusPDU], *_: Any
    ) -> bool:
        """Answer as this device is set up to."""
        self.read.append(entity.desc.key)
        if self.answers is None:
            return False
        if self.stops_after is not None and self.answered >= self.stops_after:
            # A device that answers part of a poll and then goes quiet.
            return False
        self.answered += 1
        if entity.desc.key in self.answers:
            data[entity.desc.key] = self.answers[entity.desc.key]
        return True


def _device_of(devices: list[_Device], entity: ModbusContext) -> _Device:
    """The device an entity belongs to."""
    return next(device for device in devices if entity in device.entities)


def _answers_reads(client: AsyncModbusTcpClientGateway, devices: list[_Device]) -> None:
    """Let the devices answer the reads, instead of the bus.

    Only what talks to the device is stubbed. What decides which entity is read,
    when, and what that means is the code under test.
    """

    async def _process(
        entity: ModbusContext, data: dict[str, ModbusPDU], *rest: Any
    ) -> bool:
        return await _device_of(devices, entity).process(entity, data, *rest)

    client._process_entity = AsyncMock(side_effect=_process)  # type: ignore[method-assign]


def _client(devices: list[_Device]) -> AsyncModbusTcpClientGateway:
    """A gateway client whose reads are answered by the devices given to it."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client._ensure_connection = AsyncMock(return_value=True)  # type: ignore[method-assign]
    _answers_reads(client, devices)
    return client


class _Gateway(AsyncModbusTcpClientGateway):
    """A client whose gateway connects or does not, on request.

    The connection check and its backoff are left as they are, because what is
    being tested is how often a gateway that will not answer is asked; only the
    connecting itself is stubbed, because that is what would open a socket.
    """

    # pymodbus exposes this as a read-only property, which a test cannot set.
    connected = False

    def __init__(self, *answers: bool, connected: bool = False) -> None:
        """A gateway that answers the connection attempts given to it."""
        super().__init__(host="localhost", port=123, framer=FramerType.SOCKET)
        self._cache_key = "localhost:123:socket"
        self.connected = connected
        self._answers = list(answers)
        # How often a connection was tried, which is what the backoff is for.
        self.attempts = 0

    async def connect(self) -> bool:
        """Connect, or fail, as this test has set up."""
        self.attempts += 1
        self.connected = self._answers.pop(0) if self._answers else self.connected
        return self.connected


def _gateway(*answers: bool, connected: bool = False) -> _Gateway:
    """A gateway that answers the connection attempts given to it."""
    return _Gateway(*answers, connected=connected)


def _read(client: AsyncModbusTcpClientGateway, device: _Device, **kwargs: Any) -> Any:
    """One poll of one device, as the coordinator makes it."""
    return client.update_device(device.entities, max_read_size=3, **kwargs)


@pytest.fixture(name="clock")
def clock_fixture() -> _Clock:
    """A clock only this test moves."""
    return _Clock()


@pytest.fixture(autouse=True)
def _monotonic(clock: _Clock) -> Any:
    """Let the client measure its deadlines against the test's clock."""
    with patch(f"{_MODULE}.monotonic", clock):
        yield


@pytest.mark.asyncio
async def test_a_device_that_stops_answering_is_reported_once(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """One warning when it goes, then nothing for as long as it stays away.

    A device that is off is asked again on every refresh and by every entity that
    has its own interval, and each of those asks is a line in the log saying the
    thing the first line said.
    """
    device = _Device()
    client = _client([device])
    device.answers = None

    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await _read(client, device)

    # Every refresh and every entity interval between now and the first deadline
    # reads nothing at all: the device is not talked to while it is backing off.
    for _ in range(9):
        clock.advance(0.5)
        assert await _read(client, device) == {}
        assert await client.update_device(device.entities[:1], max_read_size=3) == {}

    assert device.read == ["first"]

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "stopped answering" in warnings[0].getMessage()
    assert "Device ID 1" in warnings[0].getMessage()
    assert client.device_online(1) is False


@pytest.mark.asyncio
async def test_the_wait_before_the_next_probe_grows_and_then_stops(
    clock: _Clock,
) -> None:
    """Asked sooner and sooner would be asking a device that is not there."""
    device = _Device(answers=None)
    client = _client([device])

    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    seen: list[float] = []
    for _ in _PROBE_BACKOFF[1:]:
        clock.advance(client._outages[1].next_probe - clock.now)
        with pytest.raises(ModbusNoResponseError):
            await _read(client, device)
        seen.append(client._outages[1].next_probe - clock.now)
        assert len(device.read) == len(seen) + 1

    assert seen[0] < seen[-1]

    # Once at the last step, that is how often it is asked: an inverter that is
    # off for a night is looked at every two minutes, not every refresh.
    clock.advance(client._outages[1].next_probe - clock.now)
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)
    assert client._outages[1].next_probe - clock.now == float(_PROBE_BACKOFF[-1])


@pytest.mark.asyncio
async def test_one_probe_per_deadline(clock: _Clock) -> None:
    """The refresh and an entity's own timer cannot both probe the same device."""
    device = _Device(answers=None)
    client = _client([device])

    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)
    assert device.read == ["first"]

    # The refresh cycle and the entity timers land on the same deadline: one of
    # them asks, the others find it already being asked.
    clock.advance(_PROBE_BACKOFF[0])
    answers = await asyncio.gather(
        _read(client, device),
        _read(client, device),
        _read(client, device),
        return_exceptions=True,
    )
    assert [type(answer) for answer in answers].count(ModbusNoResponseError) == 1
    assert [answer for answer in answers if answer == {}] == [{}, {}]
    assert device.read == ["first", "first"]


@pytest.mark.asyncio
async def test_a_probe_that_is_answered_says_the_device_is_back(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """One read decides it, and the line says how long the device was gone."""
    device = _Device(answers=None)
    client = _client([device])
    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await _read(client, device)

    clock.advance(30.0)
    device.answers = {key: MagicMock(spec=ModbusPDU) for key in ("first", "second")}
    data = await _read(client, device)

    # One read of the nominated entity decides it, and the same refresh then reads
    # the rest of the device, so every entity is fresh at once rather than one now
    # and the others whenever their own timer next comes round.
    assert list(data) == ["first", "second"]
    assert device.read == ["first", "first", "second"]
    assert client.device_online(1) is True
    recoveries = [r for r in caplog.records if "is answering again" in r.getMessage()]
    assert len(recoveries) == 1
    assert "silent for 30 s" in recoveries[0].getMessage()

    # The backoff is gone, so the next refresh is a whole poll again.
    device.read.clear()
    assert await _read(client, device) == device.answers
    assert device.read == ["first", "second"]


@pytest.mark.asyncio
async def test_a_probe_that_cannot_be_used_is_not_recovery(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """An inverter coming up can answer before its registers mean anything."""
    device = _Device(answers=None)
    client = _client([device])
    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await _read(client, device)

    clock.advance(_PROBE_BACKOFF[0])
    device.answers = {}

    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    assert client.device_online(1) is False
    assert not [r for r in caplog.records if "is answering again" in r.getMessage()]


@pytest.mark.asyncio
async def test_a_device_that_answers_its_probe_and_then_goes_quiet_is_online(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """A device that answers the probe read is on the bus, and is treated as such.

    Finding a device back is one read of the entity it nominates, so a device that
    answers that and then goes quiet again has said it is there. What follows in
    the same poll is then a device answering part of a poll, which is worth
    warning about and not worth another outage: it is on the bus, the values it
    did answer are worth having, and it is polled again as normal from here.
    """
    device = _Device(answers=None)
    client = _client([device])
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    clock.advance(_PROBE_BACKOFF[0])
    device.answers = {"first": MagicMock(spec=ModbusPDU)}
    device.stops_after = 1
    caplog.clear()
    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError) as gone,
    ):
        await _read(client, device)

    # The device is back, with the one value its probe answered, and it is not on
    # a backoff: nothing here says it has gone away again.
    assert list(gone.value.partial) == ["first"]
    assert client.device_online(1) is True
    assert not client._outages
    assert (
        len([r for r in caplog.records if "is answering again" in r.getMessage()]) == 1
    )
    # What it did not answer is warned about, once, as a device answering part of
    # a poll. What is not said is that it has gone away again.
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "answered 1 of the 2" in warnings[0]
    assert "second" in warnings[0]
    assert not [message for message in warnings if "stopped answering" in message]

    # The next refresh is a whole poll, asked as normal rather than as a probe.
    device.read.clear()
    device.stops_after = None
    device.answers = {
        entity.desc.key: MagicMock(spec=ModbusPDU) for entity in device.entities
    }
    assert list(await _read(client, device)) == ["first", "second"]
    assert device.read == ["first", "second"]


@pytest.mark.asyncio
async def test_a_probe_reads_the_entity_the_device_nominates(clock: _Clock) -> None:
    """The device's own configuration says what a recovery probe should read.

    A device whose first entity is an expensive read, or one that answers slowly
    while it wakes up, should not have that asked first when all the integration
    wants to know is whether the device is back.
    """
    device = _Device(answers=None)
    client = _client([device])
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    device.read.clear()
    clock.advance(_PROBE_BACKOFF[0])
    device.answers = {
        entity.desc.key: MagicMock(spec=ModbusPDU) for entity in device.entities
    }
    data = await _read(client, device, policy=DevicePolicy(probe_key="second"))

    # Asked first, and not asked again by the poll that follows it.
    assert list(data) == ["second", "first"]
    assert device.read == ["second", "first"]
    assert client.device_online(1) is True


@pytest.mark.asyncio
async def test_a_read_of_one_entity_never_brings_a_device_back(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """Finding a device back is the refresh of the whole device's business.

    One register that is read on its own timer says nothing about the rest of the
    device, so a device that is away is not asked through an entity that has its
    own timer: those reads are stopped while it is away, and the refresh is what
    finds out whether it is back.
    """
    device = _Device(answers=None)
    client = _client([device])
    per_entity = DevicePolicy(whole_device=False)
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    device.read.clear()
    clock.advance(_PROBE_BACKOFF[0])
    device.answers = {
        entity.desc.key: MagicMock(spec=ModbusPDU) for entity in device.entities
    }
    with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
        for entity in device.entities:
            assert (
                await client.update_device(
                    [entity],
                    max_read_size=3,
                    policy=per_entity,
                )
                == {}
            )

    # Nothing was read, the device is still away, and its deadline has not moved.
    assert not device.read
    assert client.device_online(1) is False
    assert client._outages[1].failures == 1
    assert "left to the refresh of the whole device" in caplog.text

    # The refresh of the whole device is what finds it.
    assert list(
        await _read(client, device, policy=DevicePolicy(probe_key="second"))
    ) == ["second", "first"]
    assert client.device_online(1) is True


@pytest.mark.asyncio
async def test_a_read_of_one_entity_that_fails_is_not_the_device_going_away(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """One register that times out says nothing about the rest of the device.

    An entity on its own timer is read on its own, and a device with a register it
    only answers sometimes is not a device that has gone: putting it on a backoff
    over one read would take every other entity of it unavailable, and would then
    leave it on that backoff for reads that never had a chance of answering.
    """
    device = _Device()
    client = _client([device])
    device.answers = None

    per_entity = DevicePolicy(whole_device=False)
    with (
        caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await client.update_device(
            [device.entities[0]],
            max_read_size=3,
            policy=per_entity,
        )

    assert client.device_online(device.device_id) is True
    assert not client._outages
    assert "the rest of the device is untouched" in caplog.text

    # The next cycle asks again as normal, and the device is asked for everything.
    device.read.clear()
    device.answers = {
        entity.desc.key: MagicMock(spec=ModbusPDU) for entity in device.entities
    }
    assert list(await _read(client, device)) == ["first", "second"]
    assert device.read == ["first", "second"]
    assert clock.now == 0.0


@pytest.mark.asyncio
async def test_a_device_that_is_backing_off_does_not_stop_the_others(
    clock: _Clock,
) -> None:
    """A device that is off is one device. The rest of the gateway carries on."""
    inverter, meter = _Device(device_id=1), _Device(device_id=2)
    client = _client([inverter, meter])
    inverter.answers = None
    with pytest.raises(ModbusNoResponseError):
        await _read(client, inverter)

    # Every refresh that comes round inside the first wait reads nothing at all,
    # and the device behind the same gateway is not held up by any of it.
    for _ in range(4):
        clock.advance(1.0)
        assert await _read(client, inverter) == {}
        assert list(await _read(client, meter)) == ["first", "second"]


@pytest.mark.asyncio
async def test_nothing_waits_on_the_lock_while_a_device_backs_off(
    clock: _Clock,
) -> None:
    """The wait is a deadline, not a sleep.

    A sleep would be slept by every device behind this gateway that has to read
    past the lock to reach its own, so a device that is off for a night would
    quietly stop the whole gateway being polled.
    """
    device = _Device(answers=None)
    client = _client([device])
    with patch("asyncio.sleep", side_effect=AssertionError("waited")) as sleep:
        with pytest.raises(ModbusNoResponseError):
            await _read(client, device)
        for _ in range(4):
            clock.advance(1.0)
            assert await _read(client, device) == {}

    assert sleep.await_count == 0
    assert not client.lock.locked()


@pytest.mark.asyncio
async def test_a_gateway_that_will_not_connect_is_left_alone(clock: _Clock) -> None:
    """One failed connection per deadline, not one per device behind it."""
    devices = [_Device(device_id=1), _Device(device_id=2)]
    device, other = devices
    client = _gateway(False, False, True)
    _answers_reads(client, devices)

    assert await _read(client, device) == {}
    assert client.attempts == 1

    # Whatever asks in the meantime - another device, another refresh - waits.
    for _ in range(3):
        clock.advance(0.5)
        assert await _read(client, other) == {}
    assert client.attempts == 1

    # When a deadline comes the gateway is asked again, and is still not there.
    clock.advance(client._connect_next_attempt - clock.now)
    assert await _read(client, device) == {}
    assert client.attempts == 2

    clock.advance(client._connect_next_attempt - clock.now)
    assert list(await _read(client, device)) == ["first", "second"]
    assert client.attempts == 3


@pytest.mark.asyncio
async def test_a_write_does_not_wait_for_the_backoff(clock: _Clock) -> None:
    """A write is asked for by a person, and told when it did not get through.

    Nothing written is replayed when the device comes back: a write can be a
    command, and the integration does not know which kind it was.
    """
    device = _Device()
    client = _gateway(False, True)
    _answers_reads(client, [device])

    assert await client.write_data(device.entities[0], 1) is None
    assert client.attempts == 1

    # A read in the same window waits instead.
    assert await _read(client, device) == {}
    assert client.attempts == 1

    # Once the deadline comes, the read that was waiting gets through.
    clock.advance(client._connect_next_attempt - clock.now)
    assert list(await _read(client, device)) == ["first", "second"]
    assert client.attempts == 2


@pytest.mark.asyncio
async def test_a_write_to_a_device_that_stopped_answering_is_still_written(
    clock: _Clock,
) -> None:
    """The device's own backoff is about reading it, not about what is asked of it."""
    device = _Device(answers=None)
    client = _gateway(True)
    _answers_reads(client, [device])
    written: list[Any] = []

    async def _write(entity: ModbusContext, value: Any, *_: Any) -> ModbusPDU:
        written.append(value)
        answer = MagicMock(spec=ModbusPDU)
        answer.isError.return_value = False
        return answer

    client._write_holding_registers = AsyncMock(side_effect=_write)  # type: ignore[method-assign]
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)
    assert client.device_online(1) is False

    assert await client.write_data(device.entities[0], 7) is not None
    assert written == [7]

    # And nothing is replayed when it comes back.
    device.answers = {key: MagicMock(spec=ModbusPDU) for key in ("first", "second")}
    clock.advance(_PROBE_BACKOFF[0])
    await _read(client, device)
    assert written == [7]


@pytest.mark.asyncio
async def test_a_device_that_answers_part_of_a_poll_is_not_on_a_backoff(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """A device that answers 3 of 5 is on the bus, and is asked again next cycle.

    Backing off here would report an intermittent device as one that has gone,
    and would take the values it did answer down with the one it did not: the
    fault that is worth reporting is the entity that had no usable response, and
    that is warned about once per poll rather than hidden behind a backoff.
    """
    device = _Device(answers={"first": MagicMock(spec=ModbusPDU)}, stops_after=1)
    client = _client([device])

    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError) as gone,
    ):
        await _read(client, device)

    assert list(gone.value.partial) == ["first"]
    assert client.device_online(1) is True
    assert not client._outages
    warnings = [
        record
        for record in caplog.records
        if "no usable response" in record.getMessage()
    ]
    assert len(warnings) == 1
    assert "second" in warnings[0].getMessage()

    # The next poll asks the whole device as normal, and it answers again.
    device.read.clear()
    device.stops_after = None
    device.answers = {key: MagicMock(spec=ModbusPDU) for key in ("first", "second")}
    assert list(await _read(client, device)) == ["first", "second"]
    assert device.read == ["first", "second"]


@pytest.mark.asyncio
async def test_an_expected_offline_device_is_information_not_a_warning(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """A solar inverter that shuts down at dusk has done what it always does."""
    device = _Device(answers=None)
    client = _client([device])
    policy = DevicePolicy(expected_offline=True)

    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await _read(client, device, policy=policy)

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    reported = [r for r in caplog.records if "stopped answering" in r.getMessage()]
    assert len(reported) == 1
    assert reported[0].levelno == logging.INFO


@pytest.mark.asyncio
async def test_offline_online_offline_is_three_messages(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """Each change of state is reported once, in the order it happened."""
    device = _Device()
    client = _client([device])
    device.answers = None

    with (
        caplog.at_level(logging.INFO, logger=_LOGGER_NAME),
        pytest.raises(ModbusNoResponseError),
    ):
        await _read(client, device)

    device.answers = {key: MagicMock(spec=ModbusPDU) for key in ("first", "second")}
    clock.advance(_PROBE_BACKOFF[0])
    await _read(client, device)

    device.answers = None
    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)

    messages = [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.INFO
        and (
            "stopped answering" in record.getMessage()
            or "is answering again" in record.getMessage()
        )
    ]
    assert len(messages) == 3
    assert "stopped answering" in messages[0]
    assert "is answering again" in messages[1]
    assert "stopped answering" in messages[2]
    # The device is off again, and its entities are unavailable again with it.
    assert client.device_online(1) is False


@pytest.mark.asyncio
async def test_an_answer_that_cannot_be_used_is_not_an_outage(
    clock: _Clock, caplog: pytest.LogCaptureFixture
) -> None:
    """An illegal address or a short answer is a fault in the data, not the device.

    The device is on the bus and talking, so it is still answering: putting it
    in the backoff would hide a device configuration error behind "it stopped
    answering", and stop anything being read from it at all.
    """
    device = _Device(answers={})
    client = _client([device])

    with caplog.at_level(logging.INFO, logger=_LOGGER_NAME):
        assert await _read(client, device) == {}

    assert client.device_online(1) is True
    assert not client._outages
    assert [r for r in caplog.records if "no usable response" in r.getMessage()]


@pytest.mark.asyncio
async def test_a_reload_starts_with_nothing_known_about_the_device(
    clock: _Clock,
) -> None:
    """What is known lives with the connection, so a reload leaves nothing behind.

    There is no retry task to cancel either: a device is probed by whichever poll
    finds its deadline due, so a disabled or reloaded entry leaves nothing
    running and nothing to leak.
    """
    device = _Device(answers=None)
    client = _gateway(True)
    _answers_reads(client, [device])
    AsyncModbusTcpClientGateway._CLIENT[client._cache_key] = client

    with pytest.raises(ModbusNoResponseError):
        await _read(client, device)
    assert client.device_online(1) is False
    assert client._outages

    client.close_cached()

    assert client._cache_key not in AsyncModbusTcpClientGateway._CLIENT
    assert not [
        task for task in asyncio.all_tasks() if task is not asyncio.current_task()
    ]

    # The next entry to load asks for the same gateway gets a client that knows
    # nothing about the device, because nothing was written down anywhere else.
    reopened = AsyncModbusTcpClientGateway.async_get_client_connection(
        "localhost", 123, "socket"
    )
    assert reopened is not client
    assert reopened.device_online(1) is True
    AsyncModbusTcpClientGateway._CLIENT.pop(reopened._cache_key)
