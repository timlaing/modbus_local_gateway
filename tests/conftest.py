"""Fixtures for tests"""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import (
    ModbusDataType,
)
from custom_components.modbus_local_gateway.tcp_client import (
    AsyncModbusTcpClientGateway,
)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """fixture for a mock config entry"""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "localhost",
            "port": 123,
            "slave_id": 1,
            "prefix": "test",
            "filename": "test.yaml",
            "name": "simple config",
        },
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """fixture for a mock client"""
    client = AsyncMock(spec=AsyncModbusTcpClientGateway)
    client.connected = False
    return client


@pytest.fixture
def valid_entity_description() -> ModbusEntityDescription:
    """Fixture for a valid ModbusEntityDescription."""
    return ModbusEntityDescription(  # pylint: disable=unexpected-keyword-arg
        key="key",
        register_address=1,
        register_count=2,
        is_float=False,
        is_string=False,
        max_change=None,
        conv_shift_bits=None,
        conv_bits=None,
        conv_multiplier=1.0,
        precision=None,
        data_type=ModbusDataType.HOLDING_REGISTER,
    )
