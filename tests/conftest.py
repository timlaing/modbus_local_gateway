"""Fixtures for tests"""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.modbus_local_gateway.const import DOMAIN
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
