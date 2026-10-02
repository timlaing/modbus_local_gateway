# pylint: disable=too-many-lines
"""Tcp Client tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from datetime import datetime
from typing import Any, cast
from unittest.mock import AsyncMock, PropertyMock, patch

from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
    WriteSingleRegisterResponse,
)
import pytest

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.conversion import Conversion
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusBinarySensorEntityDescription,
    ModbusDateTimeEntityDescription,
    ModbusEntityDescription,
    ModbusFieldDescription,
    ModbusSelectEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    CompositeType,
    ControlType,
    ModbusDataType,
    WriteFunction,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
    ModbusClientError,
)


@pytest.mark.asyncio
async def test_read_registers_single() -> None:
    """Test the register read function"""

    response = ReadInputRegistersResponse(registers=[1])
    func = AsyncMock()
    func.return_value = response

    def __init__(self: Any, host: str) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        resp = await client.read_data(
            func=func, address=1, count=1, device_id=1, max_read_size=3
        )
        func.assert_called_once()
        assert resp == response


@pytest.mark.asyncio
async def test_read_registers_single_invalid_response_length() -> None:
    """Test the register read function"""

    response = ReadInputRegistersResponse(registers=[])
    func = AsyncMock()
    func.return_value = response

    def __init__(self: Any, host: str) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, client).read_input_registers = func
        resp = await client.read_data(
            func=func, address=1, count=1, device_id=1, max_read_size=3
        )
        func.assert_called_once()
        assert resp is None


@pytest.mark.asyncio
async def test_read_registers_single_invalid_response_type() -> None:
    """Test the register read function"""

    func = AsyncMock(return_value=None)

    def __init__(self: Any, host: str) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, client).read_input_registers = func
        resp = await client.read_data(
            func=client.read_input_registers,
            address=1,
            count=1,
            device_id=1,
            max_read_size=3,
        )
        func.assert_called_once()
        assert resp is None


@pytest.mark.asyncio
async def test_read_registers_multiple() -> None:
    """Test the register read function"""

    resp1 = ReadInputRegistersResponse()
    resp1.registers = [1, 2, 3]
    resp2 = ReadInputRegistersResponse()
    resp2.registers = [4, 5, 6]
    resp3 = ReadInputRegistersResponse()
    resp3.registers = [7, 8, 9]
    response = [resp1, resp2, resp3]
    func = AsyncMock()
    func.side_effect = response

    def __init__(self: Any, host: str) -> None:
        """Mocked init"""
        self.host = host

    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "__init__",
            __init__,
        ),
        patch.object(AsyncModbusTcpClientGateway, "read_holding_registers", func),
    ):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")

        resp = await client.read_data(
            func=func,
            address=1,
            count=9,
            device_id=1,
            max_read_size=3,
        )

        func.assert_called()
        assert resp is not None
        assert resp.registers == [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.asyncio
async def test_write_no_registers() -> None:
    """Test successful write of a single register."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[],
            device_id=1,
        )
        cast(Any, client).write_register.assert_not_called()
        mock_logger.debug.assert_called_with("No values to write, skipping.")


@pytest.mark.asyncio
async def test_write_single_register_success() -> None:
    """Test successful write of a single register."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123],
            device_id=1,
        )
        cast(Any, client).write_register.assert_called_once_with(
            address=1,
            value=123,
            device_id=1,
        )
        cast(Any, client).write_registers.assert_not_called()
        mock_logger.debug.assert_called_with("Writing successful")


@pytest.mark.asyncio
async def test_write_single_register_refused_retries_with_multiple() -> None:
    """A device that refuses FC 0x06 still gets the write, over FC 0x10.

    An exception response says the request was rejected without being carried
    out, so there is no read-back to do.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: True
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0])
    )

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        result = await client._custom_write_registers(
            address=301,
            values=[3],
            device_id=1,
        )
        cast(Any, client).write_registers.assert_called_once_with(
            address=301,
            values=[3],
            device_id=1,
        )
        cast(Any, client).read_holding_registers.assert_not_called()
        assert result is cast(Any, client).write_registers.return_value
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()


@pytest.mark.asyncio
async def test_write_single_register_unanswered_retries_with_multiple() -> None:
    """A device that ignores FC 0x06 silently gets the write, over FC 0x10.

    This is the reported symptom in #96: pymodbus retries FC 0x06 five times
    and raises ModbusIOException because nothing comes back. The read-back shows
    the register still holds its old value, so the write did not happen.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(
        side_effect=ModbusIOException("No response received after 5 retries")
    )
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0])
    )

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        result = await client._custom_write_registers(
            address=301,
            values=[3],
            device_id=1,
        )
        cast(Any, client).read_holding_registers.assert_called_once_with(
            address=301, count=1, device_id=1
        )
        cast(Any, client).write_registers.assert_called_once_with(
            address=301,
            values=[3],
            device_id=1,
        )
        assert result is cast(Any, client).write_registers.return_value
        # the reason keeps pymodbus' own diagnostics
        assert "No response received" in mock_logger.warning.call_args[0][-1]


@pytest.mark.asyncio
async def test_write_single_register_timeout_retries_with_multiple() -> None:
    """A timeout on FC 0x06 is treated the same as an unanswered write."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(side_effect=TimeoutError)
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0])
    )

    result = await client._custom_write_registers(
        address=301,
        values=[3],
        device_id=1,
    )
    cast(Any, client).write_registers.assert_called_once_with(
        address=301,
        values=[3],
        device_id=1,
    )
    assert result is cast(Any, client).write_registers.return_value


@pytest.mark.asyncio
async def test_write_single_register_unanswered_but_applied() -> None:
    """A lost response on a write that did land is not repeated.

    Writing a register can run a command, so a write whose response went missing
    must not be repeated: the read-back shows the value is there.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(
        side_effect=ModbusIOException("No response received after 5 retries")
    )
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[3])
    )

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        result = await client._custom_write_registers(
            address=301,
            values=[3],
            device_id=1,
        )
        cast(Any, client).write_registers.assert_not_called()
        assert result is not None
        assert not result.isError()
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_write_single_register_unanswered_after_fc06_worked() -> None:
    """Silence from a device that answers FC 0x06 is a lost response.

    The register read back as its old value, which on a device that implements
    preset single register means the write may have run a command and lost the
    answer. Repeating it could run the command twice (Pichler register 33
    executes Reset/Snooze and the device clears it again), so nothing is written
    a second time.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(
        return_value=WriteSingleRegisterResponse(address=301, registers=[3])
    )
    cast(Any, client).write_register.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0])
    )
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    await client._custom_write_registers(address=301, values=[3], device_id=1)

    # a device that answered FC 0x06 is remembered
    assert 1 in cast(Any, client)._devices_answering_fc06

    cast(Any, client).write_register = AsyncMock(
        side_effect=ModbusIOException("No response received after 5 retries")
    )
    with pytest.raises(ModbusClientError, match="answers preset single register"):
        await client._custom_write_registers(address=301, values=[3], device_id=1)
    cast(Any, client).write_registers.assert_not_called()


@pytest.mark.asyncio
async def test_write_single_register_unanswered_read_back_fails() -> None:
    """When the read-back fails, the write is not repeated on a guess."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(
        side_effect=ModbusIOException("No response received after 5 retries")
    )
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).read_holding_registers = AsyncMock(
        side_effect=ModbusIOException("no answer either")
    )

    with pytest.raises(ModbusClientError, match="could not be read back"):
        await client._custom_write_registers(
            address=301,
            values=[3],
            device_id=1,
        )
    cast(Any, client).write_registers.assert_not_called()


@pytest.mark.asyncio
async def test_write_single_register_fallback_also_fails() -> None:
    """Both functions refused: the FC 0x10 failure is what the caller sees.

    The fallback must not repeat FC 0x06 once more, so `write_register` is
    called exactly once.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: True
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: True

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        result = await client._custom_write_registers(
            address=301,
            values=[3],
            device_id=1,
        )
        cast(Any, client).write_register.assert_called_once()
        cast(Any, client).write_registers.assert_called_once_with(
            address=301,
            values=[3],
            device_id=1,
        )
        assert result is cast(Any, client).write_registers.return_value
        mock_logger.error.assert_called_once_with(
            "Failed to write value %d to address %d: %s",
            3,
            301,
            cast(Any, client).write_registers.return_value,
        )


@pytest.mark.asyncio
async def test_write_single_register_does_not_repeat_single_function() -> None:
    """A multi-register write that falls back to single writes keeps FC 0x06.

    FC 0x10 has already been tried by then, so the single-write fallback must
    not retry it again.
    """
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: True
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: True

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        # FC 0x10 once, then the individual writes stop at the first refusal
        cast(Any, client).write_registers.assert_called_once()
        assert cast(Any, client).write_register.call_count == 1
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_write_single_register_multiple_function() -> None:
    """A single value goes out as FC 0x10 when that function is selected."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    await client._custom_write_registers(
        address=301,
        values=[3],
        device_id=1,
        write_function=WriteFunction.MULTIPLE,
    )
    cast(Any, client).write_registers.assert_called_once_with(
        address=301,
        values=[3],
        device_id=1,
    )
    cast(Any, client).write_register.assert_not_called()


@pytest.mark.asyncio
async def test_write_single_register_single_function() -> None:
    """The default keeps a single value on FC 0x06."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    await client._custom_write_registers(
        address=301,
        values=[3],
        device_id=1,
        write_function=WriteFunction.SINGLE,
    )
    cast(Any, client).write_register.assert_called_once_with(
        address=301,
        value=3,
        device_id=1,
    )


@pytest.mark.asyncio
async def test_write_data_passes_write_function() -> None:
    """write_data forwards the entry's write function to the client."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    connected = PropertyMock(return_value=True)
    cast(Any, type(client)).connected = connected
    cast(Any, client)._custom_write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client)._custom_write_registers.return_value.isError = lambda: False

    ctx = ModbusContext(
        desc=ModbusSelectEntityDescription(
            register_address=301,
            key="output_priority",
            data_type=ModbusDataType.HOLDING_REGISTER,
            control_type=ControlType.SELECT,
            select_options={0: "UTI", 3: "SUB"},
        ),
        device_id=1,
    )

    await client.write_data(ctx, 3, write_function=WriteFunction.MULTIPLE)
    cast(Any, client)._custom_write_registers.assert_called_once_with(
        address=301,
        values=[3],
        device_id=1,
        write_function=WriteFunction.MULTIPLE,
    )


@pytest.mark.asyncio
async def test_write_multiple_registers_success() -> None:
    """Test successful write of a multiple registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        cast(Any, client).write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        mock_logger.debug.assert_called_with(
            "Writing multiple values using write_registers successful"
        )


@pytest.mark.asyncio
async def test_write_multiple_registers_failure() -> None:
    """Test failed write of a multiple registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: True
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: True

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        cast(Any, client).write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        mock_logger.error.assert_called_with(
            "Failed to write value %d to address %d: %s",
            123,
            1,
            cast(Any, client).write_register.return_value,
        )


@pytest.mark.asyncio
async def test_write_multiple_registers_success_individual() -> None:
    """Test failed write of a multiple registers, successfully individually."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: True
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        cast(Any, client).write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        mock_logger.error.assert_not_called()
        mock_logger.debug.assert_called_with(
            "All individual writes successful using fallback",
        )


@pytest.mark.asyncio
async def test_get_client() -> None:
    """test the class helper method"""

    def __init__(cls: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """Mocked init"""

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ):
        client1: AsyncModbusTcpClientGateway = (
            AsyncModbusTcpClientGateway.async_get_client_connection(
                host="A", port=1234, connection_type="socket"
            )
        )

        client2: AsyncModbusTcpClientGateway = (
            AsyncModbusTcpClientGateway.async_get_client_connection(
                host="A", port=1234, connection_type="socket"
            )
        )

        assert client1 == client2


@pytest.mark.asyncio
async def test_update_device_not_connected() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    def __init__(self: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "__init__",
            __init__,
        ),
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        connected = PropertyMock(return_value=False)
        cast(Any, type(gateway)).connected = connected

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[
                ModbusContext(
                    device_id=1,
                    desc=ModbusEntityDescription(
                        register_address=1,
                        key="key",
                        data_type=ModbusDataType.INPUT_REGISTER,
                    ),
                )
            ],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_called_once()
        debug.assert_not_called()
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_no_entities() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    def __init__(self: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "__init__",
            __init__,
        ),
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        connected = PropertyMock(return_value=True)
        cast(Any, type(gateway)).connected = connected

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        cast(Any, gateway).connect.assert_not_called()
        warning.assert_not_called()
        debug.assert_called_once()
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_success_device_single() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_data"
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        cast(Any, type(gateway)).connected = connected
        response = ReadHoldingRegistersResponse(
            registers=[
                1,
            ]
        )

        read_reg.return_value = response

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                )
            ],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        assert len(resp) == 1
        assert resp["key"] == response
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 2
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_success_device_multiple() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_data"
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        cast(Any, type(gateway)).connected = connected
        response = ReadInputRegistersResponse(
            registers=[
                1,
            ]
        )

        read_reg.return_value = response

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key3",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
            ],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        assert len(resp) == 3
        assert resp["key1"] == response
        assert resp["key2"] == response
        assert resp["key3"] == response
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 4
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_failed_device_single() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_data"
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        cast(Any, type(gateway)).connected = connected

        read_reg.side_effect = ModbusClientError(string="test")

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                )
            ],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        assert len(resp) == 0
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_called_once()
        assert debug.call_count == 2
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_failed_device_multiple() -> None:
    """Test the update device function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_data"
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        cast(Any, type(gateway)).connected = connected
        response = ReadInputRegistersResponse(
            registers=[
                3,
            ]
        )

        read_reg.side_effect = [
            response,
            ModbusClientError(string="test"),
            response,
        ]

        resp: dict[str, ModbusPDU] = await gateway.update_device(
            entities=[
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    device_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key3",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
            ],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        assert len(resp) == 2
        assert resp["key1"] == response
        assert resp["key3"] == response
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 5
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_update_device_connected_success_all_types() -> None:
    """Test update device with all four Modbus data types"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_data"
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        cast(Any, gateway).connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        cast(Any, type(gateway)).connected = connected

        responses = [
            ReadHoldingRegistersResponse(registers=[1]),
            ReadInputRegistersResponse(registers=[2]),
            ReadCoilsResponse(bits=[True]),
            ReadDiscreteInputsResponse(bits=[False]),
        ]
        read_reg.side_effect = responses

        entities = [
            ModbusContext(
                device_id=1,
                desc=ModbusSensorEntityDescription(
                    key="rw_word",
                    register_address=1,
                    data_type=ModbusDataType.HOLDING_REGISTER,
                ),
            ),
            ModbusContext(
                device_id=1,
                desc=ModbusSensorEntityDescription(
                    key="ro_word",
                    register_address=2,
                    data_type=ModbusDataType.INPUT_REGISTER,
                ),
            ),
            ModbusContext(
                device_id=1,
                desc=ModbusSwitchEntityDescription(
                    key="rw_bool",
                    register_address=3,
                    data_type=ModbusDataType.COIL,
                    control_type="switch",
                ),
            ),
            ModbusContext(
                device_id=1,
                desc=ModbusBinarySensorEntityDescription(
                    key="ro_bool",
                    register_address=4,
                    data_type=ModbusDataType.DISCRETE_INPUT,
                    control_type="binary_sensor",
                ),
            ),
        ]

        resp = await gateway.update_device(entities=entities, max_read_size=3)

        assert len(resp) == 4
        assert resp["rw_word"] == responses[0]
        assert resp["ro_word"] == responses[1]
        assert resp["rw_bool"] == responses[2]
        assert resp["ro_bool"] == responses[3]
        cast(Any, gateway).connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 5  # 4 reads + 1 completion
        assert len(lock.mock_calls) == 2


@pytest.mark.asyncio
async def test_write_data_holding_registers_success() -> None:
    """Test successful write to holding registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=2,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "connected",
            PropertyMock(return_value=True),
        ),
        patch.object(Conversion, "convert_to_registers", return_value=[123, 456]),
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER"
        ) as mock_logger,
    ):
        result: ModbusPDU | None = await client.write_data(entity, value=789)
        cast(Any, client).write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            device_id=1,
        )
        mock_logger.debug.assert_called_with(
            "Writing multiple values using write_registers successful"
        )
        # The write helpers return the PDU so write_data can detect an error
        # response; before this was fixed they always returned None, which made
        # the isError() check in write_data dead code.
        assert result is not None


@pytest.mark.asyncio
async def test_write_data_holding_registers_error_raises() -> None:
    """An error response to a register write must not be reported as success."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: True
    # Both write functions are refused, so the FC 0x10 fallback fails too
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: True

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(Conversion, "convert_to_registers", return_value=[123]),
        pytest.raises(ModbusException, match="Error writing data to test"),
    ):
        await client.write_data(entity, value=123)


@pytest.mark.asyncio
async def test_write_data_coil_error_raises() -> None:
    """An error response to a coil write must not be reported as success."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_coil = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_coil.return_value.isError = lambda: True

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.COIL,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ModbusException, match="Error writing data to test"),
    ):
        await client.write_data(entity, value=True)


@pytest.mark.asyncio
async def test_write_data_coils_success() -> None:
    """Test successful write to coils."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_coil = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_coil.return_value.isError = lambda: False

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.COIL,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER"
        ) as mock_logger,
    ):
        result = await client.write_data(entity, value=True)
        cast(Any, client).write_coil.assert_called_once_with(
            address=1,
            value=True,
            device_id=1,
        )
        mock_logger.debug.assert_called_with(
            "Value before conversion: %s (type: %s)",
            True,
            "bool",
        )
        assert result is not None


@pytest.mark.asyncio
async def test_write_data_failed_connection() -> None:
    """Test failed connection."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=False)
        ),
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER"
        ) as mock_logger,
    ):
        result: ModbusPDU | None = await client.write_data(entity, value=123)
        cast(Any, client).connect.assert_called_once()
        mock_logger.warning.assert_called_with(
            "Failed to connect to gateway - %s", client
        )
        assert result is None


@pytest.mark.asyncio
async def test_write_data_unsupported_data_type() -> None:
    """Test unsupported data type."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=cast(Any, "unsupported"),
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ValueError, match="Unsupported data type: unsupported"),
    ):
        await client.write_data(entity, value=123)


@pytest.mark.asyncio
async def test_write_data_incorrect_register_count() -> None:
    """Test incorrect register count."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=2,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(Conversion, "convert_to_registers", return_value=[123]),
        pytest.raises(
            ModbusException, match="Incorrect number of registers: expected 2, got 1"
        ),
    ):
        await client.write_data(entity, value=789)


@pytest.mark.asyncio
async def test_write_data_invalid_coil_value_type() -> None:
    """Test invalid coil value type."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.COIL,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(TypeError, match="Value for COIL must be boolean, got int"),
    ):
        await client.write_data(entity, value=123)


def _bitfield_entity() -> ModbusContext:
    """A switch on bit 4 of a holding register."""
    return ModbusContext(
        device_id=1,
        desc=ModbusSwitchEntityDescription(
            key="bitfield",
            register_address=1,
            register_count=1,
            control_type="switch",
            data_type=ModbusDataType.HOLDING_REGISTER,
            conv_bits=1,
            conv_shift_bits=4,
            on=1,
            off=0,
        ),
    )


@pytest.mark.asyncio
async def test_write_data_bitfield_read_modify_write() -> None:
    """Writing a bit field reads the register and merges into it."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(
            AsyncModbusTcpClientGateway,
            "read_data",
            AsyncMock(
                return_value=ReadHoldingRegistersResponse(registers=[0b0000_0011])
            ),
        ),
    ):
        await client.write_data(_bitfield_entity(), value=1)

        # bit 4 set, the two bits already on are untouched
        cast(Any, client).write_register.assert_called_once_with(
            address=1,
            value=0b0001_0011,
            device_id=1,
        )


@pytest.mark.asyncio
async def test_write_data_bitfield_read_failure_aborts_write() -> None:
    """A failed read must abort - merging onto a guess would clear the field's
    neighbours, which is worse than not writing at all."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(
            AsyncModbusTcpClientGateway, "read_data", AsyncMock(return_value=None)
        ),
        pytest.raises(ModbusException, match="aborting bit field write"),
    ):
        await client.write_data(_bitfield_entity(), value=1)

    cast(Any, client).write_register.assert_not_called()


@pytest.mark.asyncio
async def test_write_data_bitfield_error_response_aborts_write() -> None:
    """An error PDU from the read is a failed read, not a value of zero."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())

    error_response = ReadHoldingRegistersResponse(registers=[0])
    cast(Any, error_response).isError = lambda: True

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(
            AsyncModbusTcpClientGateway,
            "read_data",
            AsyncMock(return_value=error_response),
        ),
        pytest.raises(ModbusException, match="aborting bit field write"),
    ):
        await client.write_data(_bitfield_entity(), value=1)

    cast(Any, client).write_register.assert_not_called()


@pytest.mark.asyncio
async def test_write_data_non_bitfield_does_not_read_first() -> None:
    """Plain registers keep the single-transaction write they always had."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_register = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_register.return_value.isError = lambda: False

    entity = ModbusContext(
        device_id=1,
        desc=ModbusEntityDescription(
            key="plain",
            register_address=1,
            register_count=1,
            data_type=ModbusDataType.HOLDING_REGISTER,
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        patch.object(
            AsyncModbusTcpClientGateway, "read_data", AsyncMock()
        ) as read_data,
    ):
        await client.write_data(entity, value=123)

        read_data.assert_not_called()
        cast(Any, client).write_register.assert_called_once()


def _composite_entity(
    fields: tuple[tuple[str, int], ...] = (
        ("year", 45),
        ("month", 46),
        ("day", 47),
        ("hour", 48),
        ("minute", 49),
        ("second", 50),
    ),
    data_type: ModbusDataType = ModbusDataType.HOLDING_REGISTER,
) -> ModbusContext:
    """Build a composite clock entity from (field name, address) pairs"""
    addresses = [address for _, address in fields]
    return ModbusContext(
        device_id=1,
        desc=ModbusDateTimeEntityDescription(
            key="clock",
            register_address=min(addresses),
            register_count=max(addresses) - min(addresses) + 1,
            data_type=data_type,
            control_type=ControlType.DATETIME,
            composite_type=CompositeType.DATETIME,
            fields=tuple(
                ModbusFieldDescription(key=name, address=address)
                for name, address in fields
            ),
        ),
    )


@pytest.mark.asyncio
async def test_read_composite_contiguous_is_one_request() -> None:
    """Adjacent composite fields are read in a single request"""
    client = AsyncModbusTcpClientGateway(host="127.0.0.1")
    read = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[2026, 9, 22, 16, 30, 5])
    )

    response = await client._read_composite_runs(_composite_entity(), read, 64)

    read.assert_called_once()
    assert read.call_args.kwargs["address"] == 45
    assert read.call_args.kwargs["count"] == 6
    assert list(response.registers) == [2026, 9, 22, 16, 30, 5]


@pytest.mark.asyncio
async def test_read_composite_gapped_runs_are_stitched() -> None:
    """Fields that are not adjacent are read per run and stitched together"""
    client = AsyncModbusTcpClientGateway(host="127.0.0.1")
    read = AsyncMock(
        side_effect=[
            ReadHoldingRegistersResponse(registers=[2026, 9, 22]),
            ReadHoldingRegistersResponse(registers=[16, 30, 5]),
        ]
    )

    response = await client._read_composite_runs(
        _composite_entity(
            fields=(
                ("year", 45),
                ("month", 46),
                ("day", 47),
                ("hour", 60),
                ("minute", 61),
                ("second", 62),
            )
        ),
        read,
        64,
    )

    assert read.call_count == 2
    assert read.call_args_list[0].kwargs["address"] == 45
    assert read.call_args_list[0].kwargs["count"] == 3
    assert read.call_args_list[1].kwargs["address"] == 60
    assert read.call_args_list[1].kwargs["count"] == 3
    # the registers between the runs are not read, so they stay zero
    assert list(response.registers) == [2026, 9, 22] + [0] * 12 + [16, 30, 5]


@pytest.mark.asyncio
async def test_read_composite_input_register_response_type() -> None:
    """An input register composite reads with the input response type"""
    client = AsyncModbusTcpClientGateway(host="127.0.0.1")
    read = AsyncMock(return_value=ReadInputRegistersResponse(registers=[2026, 9, 22]))

    response = await client._read_composite_runs(
        _composite_entity(
            fields=(("year", 45), ("month", 46), ("day", 47)),
            data_type=ModbusDataType.INPUT_REGISTER,
        ),
        read,
        64,
    )

    assert isinstance(response, ReadInputRegistersResponse)
    assert list(response.registers) == [2026, 9, 22]


@pytest.mark.asyncio
async def test_read_composite_run_error_raises() -> None:
    """An error response for one run must not be reported as a value"""
    client = AsyncModbusTcpClientGateway(host="127.0.0.1")
    error_response = ReadHoldingRegistersResponse(registers=[0])
    cast(Any, error_response).isError = lambda: True
    read = AsyncMock(return_value=error_response)
    entity = _composite_entity()

    with pytest.raises(ModbusClientError, match="Error reading composite clock"):
        await client._read_composite_runs(entity, read, 64)


@pytest.mark.asyncio
async def test_read_composite_no_response_raises() -> None:
    """A missing response must not be reported as a value"""
    client = AsyncModbusTcpClientGateway(host="127.0.0.1")
    read = AsyncMock(return_value=None)
    entity = _composite_entity()

    with pytest.raises(ModbusClientError, match="No response reading composite clock"):
        await client._read_composite_runs(entity, read, 64)


@pytest.mark.asyncio
async def test_process_entity_reads_composite() -> None:
    """Polling a composite entity goes through the run reader"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    data: dict[str, Any] = {}

    with patch.object(
        AsyncModbusTcpClientGateway,
        "read_data",
        AsyncMock(return_value=ReadHoldingRegistersResponse(registers=[2026, 9, 22])),
    ):
        await client._process_entity(
            _composite_entity(fields=(("year", 45), ("month", 46), ("day", 47))),
            data,
            0,
            64,
        )

    assert list(data["clock"].registers) == [2026, 9, 22]


@pytest.mark.asyncio
async def test_process_entity_composite_read_error() -> None:
    """A composite whose run read fails is not stored as data"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    data: dict[str, Any] = {}
    error_response = ReadHoldingRegistersResponse(registers=[])
    cast(Any, error_response).isError = lambda: True

    with (
        patch.object(
            AsyncModbusTcpClientGateway,
            "read_data",
            AsyncMock(return_value=error_response),
        ),
        patch("custom_components.modbus_local_gateway.tcp_client._LOGGER") as logger,
    ):
        await client._process_entity(
            _composite_entity(fields=(("year", 45), ("month", 46), ("day", 47))),
            data,
            0,
            64,
        )

    assert "clock" not in data
    assert logger.warning.call_count == 1


@pytest.mark.asyncio
async def test_write_composite_contiguous_is_one_request() -> None:
    """One value writes every adjacent field in a single request"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False

    with patch.object(
        AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
    ):
        await client.write_data(
            _composite_entity(), value=datetime(2026, 9, 22, 16, 30, 5)
        )

    cast(Any, client).write_registers.assert_called_once_with(
        address=45, values=[2026, 9, 22, 16, 30, 5], device_id=1
    )


@pytest.mark.asyncio
async def test_write_composite_gapped_runs() -> None:
    """Each run of adjacent fields is written with its own request"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())
    cast(Any, client).write_registers.return_value.isError = lambda: False

    with patch.object(
        AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
    ):
        await client.write_data(
            _composite_entity(
                fields=(
                    ("year", 45),
                    ("month", 46),
                    ("day", 47),
                    ("hour", 60),
                    ("minute", 61),
                    ("second", 62),
                )
            ),
            value=datetime(2026, 9, 22, 16, 30, 5),
        )

    assert cast(Any, client).write_registers.call_count == 2
    assert cast(Any, client).write_registers.call_args_list[0].kwargs == {
        "address": 45,
        "values": [2026, 9, 22],
        "device_id": 1,
    }
    assert cast(Any, client).write_registers.call_args_list[1].kwargs == {
        "address": 60,
        "values": [16, 30, 5],
        "device_id": 1,
    }


@pytest.mark.asyncio
async def test_write_composite_error_response_aborts_write() -> None:
    """An error response for a run must not be reported as a successful write"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    error_response = ModbusPDU()
    cast(Any, error_response).isError = lambda: True
    # Both write functions are refused, so the FC 0x10 fallback fails too
    cast(Any, client).write_registers = AsyncMock(return_value=error_response)
    cast(Any, client).write_register = AsyncMock(return_value=error_response)

    entity = _composite_entity()
    value = datetime(2026, 9, 22, 16, 30, 5)

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ModbusClientError, match="Error writing clock"),
    ):
        await client.write_data(entity, value=value)


@pytest.mark.asyncio
async def test_write_composite_input_register_is_refused() -> None:
    """A read-only composite cannot be written"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    entity = _composite_entity(
        fields=(("year", 45), ("month", 46), ("day", 47)),
        data_type=ModbusDataType.INPUT_REGISTER,
    )
    value = datetime(2026, 9, 22, 16, 30, 5)

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ModbusClientError, match="cannot be written"),
    ):
        await client.write_data(entity, value=value)

    cast(Any, client).write_registers.assert_not_called()


def _packed_composite_entity(
    address: int = 3038, data_type: ModbusDataType = ModbusDataType.HOLDING_REGISTER
) -> ModbusContext:
    """Build the Growatt period 1 word: minute bits 0-7, hour bits 8-12.

    Bits 13-14 are the charge mode and bit 15 the enable, described by other
    entities rather than by this composite.
    """
    return ModbusContext(
        device_id=1,
        desc=ModbusDateTimeEntityDescription(
            key="period1_end",
            register_address=address,
            register_count=1,
            data_type=data_type,
            control_type=ControlType.DATETIME,
            composite_type=CompositeType.TIME,
            fields=(
                ModbusFieldDescription(
                    key="minute", address=address, conv_bits=8, conv_shift_bits=0
                ),
                ModbusFieldDescription(
                    key="hour", address=address, conv_bits=5, conv_shift_bits=8
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_write_composite_bit_fields_keep_other_bits() -> None:
    """Writing a packed time leaves the mode and enable bits alone"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    read_holding = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0xC900])
    )
    cast(Any, client).read_holding_registers = read_holding
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    with patch.object(
        AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
    ):
        await client.write_data(
            _packed_composite_entity(),
            value=datetime(2026, 9, 22, 22, 45),
        )

    # 0xC900 is mode Grid (bits 13-14) and enabled (bit 15); the merged write
    # keeps both and only replaces the hour and minute.
    cast(Any, client).write_registers.assert_called_once_with(
        address=3038, values=[0xD62D], device_id=1
    )
    assert read_holding.call_args.kwargs["count"] == 1


@pytest.mark.asyncio
async def test_write_composite_bit_fields_need_no_read_when_none() -> None:
    """A composite without bit fields is written without reading first"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).read_holding_registers = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    with patch.object(
        AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
    ):
        await client.write_data(
            _composite_entity(), value=datetime(2026, 9, 22, 16, 30, 5)
        )

    cast(Any, client).read_holding_registers.assert_not_called()


@pytest.mark.asyncio
async def test_write_composite_bit_field_read_failure_aborts() -> None:
    """A failed merge read must not write onto a guess"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    error_response = ModbusPDU()
    cast(Any, error_response).isError = lambda: True
    cast(Any, client).read_holding_registers = AsyncMock(return_value=error_response)
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    entity = _packed_composite_entity()
    value = datetime(2026, 9, 22, 22, 45)
    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ModbusClientError, match="aborting bit field write"),
    ):
        await client.write_data(entity, value=value)

    cast(Any, client).write_registers.assert_not_called()


@pytest.mark.asyncio
async def test_write_composite_bit_fields_span_read_once() -> None:
    """A composite with a bit field reads its whole span in one transaction"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    read_holding = AsyncMock(
        return_value=ReadHoldingRegistersResponse(registers=[0xC900, 0xC700])
    )
    cast(Any, client).read_holding_registers = read_holding
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    entity = ModbusContext(
        device_id=1,
        desc=ModbusDateTimeEntityDescription(
            key="clock",
            register_address=3038,
            register_count=2,
            data_type=ModbusDataType.HOLDING_REGISTER,
            control_type=ControlType.DATETIME,
            composite_type=CompositeType.TIME,
            fields=(
                ModbusFieldDescription(
                    key="hour", address=3038, conv_bits=5, conv_shift_bits=8
                ),
                ModbusFieldDescription(key="minute", address=3039),
            ),
        ),
    )
    with patch.object(
        AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
    ):
        await client.write_data(entity, value=datetime(2026, 9, 22, 16, 30))

    # The second register is written from the value, the first keeps its mode
    # and enable bits.
    cast(Any, client).write_registers.assert_called_once_with(
        address=3038, values=[0xD000, 30], device_id=1
    )
    assert read_holding.call_args.kwargs["count"] == 2
    cast(Any, client).read_holding_registers.assert_called_once()


@pytest.mark.asyncio
async def test_write_composite_input_register_bit_fields_refused() -> None:
    """A read-only composite of bit fields is still refused"""
    client = AsyncModbusTcpClientGateway(host="localhost")
    cast(Any, client).connect = AsyncMock()
    cast(Any, client).read_holding_registers = AsyncMock()
    cast(Any, client).write_registers = AsyncMock(return_value=ModbusPDU())

    entity = _packed_composite_entity(data_type=ModbusDataType.INPUT_REGISTER)
    value = datetime(2026, 9, 22, 22, 45)
    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ModbusClientError, match="cannot be written"),
    ):
        await client.write_data(entity, value=value)

    cast(Any, client).read_holding_registers.assert_not_called()
    cast(Any, client).write_registers.assert_not_called()
