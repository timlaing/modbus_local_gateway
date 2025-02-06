"""Tcp Client tests"""

from unittest.mock import AsyncMock, PropertyMock, patch

from pymodbus.exceptions import ModbusException
from pymodbus.pdu.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
)

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)


async def test_read_registers_single() -> None:
    """Test the register read function"""

    response = ReadInputRegistersResponse()
    func = AsyncMock()
    func.return_value = response

    def __init__(self, host) -> None:
        """Mocked init"""
        self.host = host

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")

        resp: ModbusPDU | None = await client.read_registers(
            func=func, address=1, count=1, slave=1, max_read_size=3
        )

        func.assert_called_once()
        assert resp is not None
        assert resp == response


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

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")

        resp = await client.read_registers(
            func=func, address=1, count=9, slave=1, max_read_size=3
        )

        func.assert_called()
        assert resp is not None
        assert resp.registers == [1, 2, 3, 4, 5, 6, 7, 8, 9]


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

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=False)
        type(gateway).connected = connected  # type: ignore

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[], max_read_size=3
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

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
        type(gateway).connected = connected  # type: ignore

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[], max_read_size=3
        )

        assert resp is not None
        assert isinstance(resp, dict)
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        debug.assert_called_once()
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_sucess_slave_single() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug, patch(
        (
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_registers"
        )
    ) as read_reg:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
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
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key",
                        register_address=1,
                        register_count=1,
                        holding_register=True,
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

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug, patch(
        (
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_registers"
        )
    ) as read_reg:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
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
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key1",
                        register_address=1,
                        register_count=1,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key2",
                        register_address=1,
                        register_count=1,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key3",
                        register_address=1,
                        register_count=1,
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

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug, patch(
        (
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_registers"
        )
    ) as read_reg:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
        type(gateway).connected = connected  # type: ignore

        read_reg.side_effect = ModbusException(string="test")

        resp: dict[str, ModbusPDU] = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key",
                        register_address=1,
                        register_count=1,
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
        assert debug.call_count == 1
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_failed_slave_multiple() -> None:
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Mocked init"""
        self.lock = lock

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ), patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.warning"
    ) as warning, patch(
        "custom_components.modbus_local_gateway.tcp_client._LOGGER.debug"
    ) as debug, patch(
        (
            "custom_components.modbus_local_gateway.tcp_client."
            "AsyncModbusTcpClientGateway.read_registers"
        )
    ) as read_reg:
        gateway = AsyncModbusTcpClientGateway(host="127.0.0.1")
        gateway.connect = AsyncMock()
        connected = PropertyMock(return_value=True)
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
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key1",
                        register_address=1,
                        register_count=1,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key2",
                        register_address=1,
                        register_count=1,
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(  # pylint: disable=unexpected-keyword-arg
                        key="key3",
                        register_address=1,
                        register_count=1,
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
