"""Tcp Client tests"""

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from pymodbus.exceptions import ModbusException
from pymodbus.pdu.bit_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.conversion import Conversion
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusBinarySensorEntityDescription,
    ModbusDataType,
    ModbusEntityDescription,
    ModbusSensorEntityDescription,
    ModbusSwitchEntityDescription,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)

# pylint: disable=unexpected-keyword-arg
# pylint: disable=protected-access


async def test_read_registers_single() -> None:
    """Test the register read function"""

    response = ReadInputRegistersResponse(registers=[1])
    func = AsyncMock()
    func.return_value = response

    def __init__(self, host) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        resp = await client.read_data(
            func=func, address=1, count=1, slave=1, max_read_size=3
        )
        func.assert_called_once()
        assert resp == response


async def test_read_registers_single_invalid_response_length() -> None:
    """Test the register read function"""

    response = ReadInputRegistersResponse(registers=[])
    func = AsyncMock()
    func.return_value = response

    def __init__(self, host) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        client.read_input_registers = func
        resp = await client.read_data(
            func=func, address=1, count=1, slave=1, max_read_size=3
        )
        func.assert_called_once()
        assert resp is None


async def test_read_registers_single_invalid_response_type() -> None:
    """Test the register read function"""

    func = AsyncMock(return_value=None)

    def __init__(self, host) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(AsyncModbusTcpClientGateway, "__init__", __init__):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")
        client.read_input_registers = func
        resp = await client.read_data(
            func=client.read_input_registers,
            address=1,
            count=1,
            slave=1,
            max_read_size=3,
        )
        func.assert_called_once()
        assert resp is None


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

    def __init__(self, host) -> None:
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
            slave=1,
            max_read_size=3,
        )

        func.assert_called()
        assert resp is not None
        assert resp.registers == [1, 2, 3, 4, 5, 6, 7, 8, 9]


async def test_write_no_registers() -> None:
    """Test successful write of a single register."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_register = AsyncMock(return_value=ModbusPDU())
    client.write_register.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[],
            slave=1,
        )
        client.write_register.assert_not_called()
        mock_logger.debug.assert_called_with("No values to write, skipping.")


async def test_write_single_register_success() -> None:
    """Test successful write of a single register."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_register = AsyncMock(return_value=ModbusPDU())
    client.write_register.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123],
            slave=1,
        )
        client.write_register.assert_called_once_with(
            address=1,
            value=123,
            slave=1,
        )
        mock_logger.debug.assert_called_with("Writing successful")


async def test_write_single_register_failure() -> None:
    """Test failed write of a single register."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_register = AsyncMock(return_value=ModbusPDU())
    client.write_register.return_value.isError = lambda: True

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123],
            slave=1,
        )
        client.write_register.assert_called_once_with(
            address=1,
            value=123,
            slave=1,
        )
        mock_logger.error.assert_called_with(
            "Failed to write value %d to address %d: %s",
            123,
            1,
            client.write_register.return_value,
        )


async def test_write_multiple_registers_success() -> None:
    """Test successful write of a multiple registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_registers = AsyncMock(return_value=ModbusPDU())
    client.write_registers.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            slave=1,
        )
        client.write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            slave=1,
        )
        mock_logger.debug.assert_called_with(
            "Writing multiple values using write_registers successful"
        )


async def test_write_multiple_registers_failure() -> None:
    """Test failed write of a multiple registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_registers = AsyncMock(return_value=ModbusPDU())
    client.write_registers.return_value.isError = lambda: True
    client.write_register = AsyncMock(return_value=ModbusPDU())
    client.write_register.return_value.isError = lambda: True

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            slave=1,
        )
        client.write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            slave=1,
        )
        mock_logger.error.assert_called_with(
            "Failed to write value %d to address %d: %s",
            123,
            1,
            client.write_register.return_value,
        )


async def test_write_multiple_registers_success_individual() -> None:
    """Test failed write of a multiple registers, successfully individually."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.write_registers = AsyncMock(return_value=ModbusPDU())
    client.write_registers.return_value.isError = lambda: True
    client.write_register = AsyncMock(return_value=ModbusPDU())
    client.write_register.return_value.isError = lambda: False

    with patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER"
    ) as mock_logger:
        await client._custom_write_registers(
            address=1,
            values=[123, 456],
            slave=1,
        )
        client.write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            slave=1,
        )
        mock_logger.error.assert_not_called()
        mock_logger.debug.assert_called_with(
            "All individual writes successful using fallback",
        )


async def test_get_client() -> None:
    """test the class helper method"""

    def __init__(cls, **kwargs) -> None:  # pylint: disable=unused-argument
        """Mocked init"""

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ):
        client1: AsyncModbusTcpClientGateway = (
            AsyncModbusTcpClientGateway.async_get_client_connection(host="A", port=1234)
        )

        client2: AsyncModbusTcpClientGateway = (
            AsyncModbusTcpClientGateway.async_get_client_connection(host="A", port=1234)
        )

        assert client1 == client2


async def test_update_slave_not_connected() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
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
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=False)
        type(gateway).connected = connected  # type: ignore

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
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
        gateway.connect.assert_called_once()
        warning.assert_called_once()
        debug.assert_not_called()
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_no_entities() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
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
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
        type(gateway).connected = connected  # type: ignore

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[],
            max_read_size=3,
        )

        assert resp is not None
        assert isinstance(resp, dict)
        gateway.connect.assert_not_called()
        warning.assert_not_called()
        debug.assert_called_once()
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_sucess_slave_single() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            (
                "custom_components.modbus_local_gateway.tcp_client."
                "AsyncModbusTcpClientGateway.read_data"
            )
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        type(gateway).connected = connected  # type: ignore
        response = ReadHoldingRegistersResponse(
            registers=[
                1,
            ]
        )

        read_reg.return_value = response

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
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
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 2
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_sucess_slave_multiple() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            (
                "custom_components.modbus_local_gateway.tcp_client."
                "AsyncModbusTcpClientGateway.read_data"
            )
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        type(gateway).connected = connected  # type: ignore
        response = ReadInputRegistersResponse(
            registers=[
                1,
            ]
        )

        read_reg.return_value = response

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
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
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 4
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_failed_slave_single() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            (
                "custom_components.modbus_local_gateway.tcp_client."
                "AsyncModbusTcpClientGateway.read_data"
            )
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        type(gateway).connected = connected  # type: ignore

        read_reg.side_effect = ModbusException(string="test")

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
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
        gateway.connect.assert_called_once()
        warning.assert_called_once()
        assert debug.call_count == 2
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_failed_slave_multiple() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    with (
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
        ) as warning,
        patch(
            "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
        ) as debug,
        patch(
            (
                "custom_components.modbus_local_gateway.tcp_client."
                "AsyncModbusTcpClientGateway.read_data"
            )
        ) as read_reg,
    ):
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        type(gateway).connected = connected  # type: ignore
        response = ReadInputRegistersResponse(
            registers=[
                3,
            ]
        )

        read_reg.side_effect = [response, ModbusException(string="test"), response]

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2",
                        register_address=1,
                        register_count=1,
                        data_type=ModbusDataType.HOLDING_REGISTER,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
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
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 5
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_success_all_types() -> None:
    """Test update slave with all four Modbus data types"""
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
        gateway.connect = AsyncMock()
        gateway.lock = lock
        connected = PropertyMock(side_effect=[False, True])
        type(gateway).connected = connected  # type: ignore

        responses = [
            ReadHoldingRegistersResponse(registers=[1]),
            ReadInputRegistersResponse(registers=[2]),
            ReadCoilsResponse(bits=[True]),
            ReadDiscreteInputsResponse(bits=[False]),
        ]
        read_reg.side_effect = responses

        entities = [
            ModbusContext(
                slave_id=1,
                desc=ModbusSensorEntityDescription(
                    key="rw_word",
                    register_address=1,
                    data_type=ModbusDataType.HOLDING_REGISTER,
                ),
            ),
            ModbusContext(
                slave_id=1,
                desc=ModbusSensorEntityDescription(
                    key="ro_word",
                    register_address=2,
                    data_type=ModbusDataType.INPUT_REGISTER,
                ),
            ),
            ModbusContext(
                slave_id=1,
                desc=ModbusSwitchEntityDescription(
                    key="rw_bool",
                    register_address=3,
                    data_type=ModbusDataType.COIL,
                    control_type="switch",
                ),
            ),
            ModbusContext(
                slave_id=1,
                desc=ModbusBinarySensorEntityDescription(
                    key="ro_bool",
                    register_address=4,
                    data_type=ModbusDataType.DISCRETE_INPUT,
                    control_type="binary_sensor",
                ),
            ),
        ]

        resp = await gateway.update_slave(entities=entities, max_read_size=3)

        assert len(resp) == 4
        assert resp["rw_word"] == responses[0]
        assert resp["ro_word"] == responses[1]
        assert resp["rw_bool"] == responses[2]
        assert resp["ro_bool"] == responses[3]
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        assert debug.call_count == 5  # 4 reads + 1 completion
        assert len(lock.mock_calls) == 2


async def test_write_data_holding_registers_success() -> None:
    """Test successful write to holding registers."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()
    client.write_registers = AsyncMock(return_value=ModbusPDU())
    client.write_registers.return_value.isError = lambda: False

    entity = ModbusContext(
        slave_id=1,
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
        client.write_registers.assert_called_once_with(
            address=1,
            values=[123, 456],
            slave=1,
        )
        mock_logger.debug.assert_called_with(
            "Writing multiple values using write_registers successful"
        )
        assert result is None


async def test_write_data_coils_success() -> None:
    """Test successful write to coils."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()
    client.write_coil = AsyncMock(return_value=ModbusPDU())
    client.write_coil.return_value.isError = lambda: False

    entity = ModbusContext(
        slave_id=1,
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
        client.write_coil.assert_called_once_with(
            address=1,
            value=True,
            slave=1,
        )
        mock_logger.debug.assert_called_with(
            "Value before conversion: %s (type: %s)",
            True,
            "bool",
        )
        assert result is not None


async def test_write_data_failed_connection() -> None:
    """Test failed connection."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()

    entity = ModbusContext(
        slave_id=1,
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
        client.connect.assert_called_once()
        mock_logger.warning.assert_called_with(
            "Failed to connect to gateway - %s", client
        )
        assert result is None


async def test_write_data_unsupported_data_type() -> None:
    """Test unsupported data type."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()

    entity = ModbusContext(
        slave_id=1,
        desc=ModbusEntityDescription(
            key="test",
            register_address=1,
            register_count=1,
            data_type="unsupported",  # type: ignore
        ),
    )

    with (
        patch.object(
            AsyncModbusTcpClientGateway, "connected", PropertyMock(return_value=True)
        ),
        pytest.raises(ValueError, match="Unsupported data type: unsupported"),
    ):
        await client.write_data(entity, value=123)


async def test_write_data_incorrect_register_count() -> None:
    """Test incorrect register count."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()

    entity = ModbusContext(
        slave_id=1,
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


async def test_write_data_invalid_coil_value_type() -> None:
    """Test invalid coil value type."""
    client = AsyncModbusTcpClientGateway(host="localhost")
    client.connect = AsyncMock()

    entity = ModbusContext(
        slave_id=1,
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
