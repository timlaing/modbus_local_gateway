"""Tcp Client tests"""

from unittest.mock import AsyncMock, PropertyMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ModbusResponse

from custom_components.modbus_local_gateway.context import ModbusContext
from custom_components.modbus_local_gateway.sensor_types.base import (
    ModbusSensorEntityDescription,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClient,
    AsyncModbusTcpClientGateway,
)


async def test_read_registers_single():
    """Test the register read function"""

    response = ModbusResponse()
    func = AsyncMock()
    func.return_value = response

    def __init__(*_):
        """Mocked init"""

    with patch.object(
        AsyncModbusTcpClient,
        "__init__",
        __init__,
    ):
        client = AsyncModbusTcpClientGateway(host="127.0.0.1")

        resp = await client.read_registers(
            func=func, address=1, count=1, slave=1, max_read_size=3
        )

        func.assert_called_once()
        assert resp is not None
        assert resp == response


async def test_read_registers_multiple():
    """Test the register read function"""

    resp1 = ModbusResponse()
    resp1.registers = [1, 2, 3]
    resp2 = ModbusResponse()
    resp2.registers = [4, 5, 6]
    resp3 = ModbusResponse()
    resp3.registers = [7, 8, 9]
    response = [resp1, resp2, resp3]
    func = AsyncMock()
    func.side_effect = response

    def __init__(self, host):
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


async def test_get_client():
    """test the class helper method"""

    def __init__(cls, **kwargs):  # pylint: disable=unused-argument
        """Mocked init"""

    with patch.object(
        AsyncModbusTcpClientGateway,
        "__init__",
        __init__,
    ):
        data = {CONF_HOST: "A", CONF_PORT: 1234}
        client1 = await AsyncModbusTcpClientGateway.async_get_client_connection(
            hass=None, data=data
        )

        client2 = await AsyncModbusTcpClientGateway.async_get_client_connection(
            hass=None, data=data
        )

        assert client1 == client2


async def test_update_slave_not_connected():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected

        resp = await gateway.update_slave(entities=[], max_read_size=3)

        assert resp is not None
        assert isinstance(resp, dict)
        gateway.connect.assert_called_once()
        warning.assert_called_once()
        debug.assert_not_called()
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_no_entities():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected

        resp = await gateway.update_slave(entities=[], max_read_size=3)

        assert resp is not None
        assert isinstance(resp, dict)
        gateway.connect.assert_called_once()
        warning.assert_not_called()
        debug.assert_called_once()
        assert len(lock.mock_calls) == 2


async def test_update_slave_connected_sucess_slave_single():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected
        response = ModbusResponse()

        read_reg.return_value = response

        resp = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key", register_address=1, register_count=1
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


async def test_update_slave_connected_sucess_slave_multiple():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected
        response = ModbusResponse()

        read_reg.return_value = response

        resp = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1", register_address=1, register_count=1
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2", register_address=1, register_count=1
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key3", register_address=1, register_count=1
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


async def test_update_slave_connected_failed_slave_single():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected

        read_reg.side_effect = ModbusException(string="test")

        resp = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key", register_address=1, register_count=1
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


async def test_update_slave_connected_failed_slave_multiple():
    """Test the update slave function"""
    lock = AsyncMock()

    def __init__(self, **kwargs):  # pylint: disable=unused-argument
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
        type(gateway).connected = connected
        response = ModbusResponse()

        read_reg.side_effect = [response, ModbusException(string="test"), response]

        resp = await gateway.update_slave(
            entities=[
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key1", register_address=1, register_count=1
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key2", register_address=1, register_count=1
                    ),
                ),
                ModbusContext(
                    slave_id=1,
                    desc=ModbusSensorEntityDescription(
                        key="key3", register_address=1, register_count=1
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
        warning.assert_called_once()
        assert debug.call_count == 4
        assert len(lock.mock_calls) == 2
