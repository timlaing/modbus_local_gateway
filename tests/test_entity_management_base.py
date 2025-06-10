"""Unit tests for the `ModbusEntityDescription` class in the `entity_management.base` module.
These tests cover various scenarios to ensure the validation logic works as expected."""

from unittest.mock import patch

from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
)

# pylint: disable=unexpected-keyword-arg
# pylint: disable=protected-access


def test_validate_both_float_and_string(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when both is_float and is_string are True."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{**entity.__dict__, "is_float": True, "is_string": True}
    )
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once_with(
            "Unable to create entity for %s: Both string and float defined",
            entity.key,
        )


def test_validate_invalid_string_conversion(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when is_string is True with invalid conversion parameters."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(**{**entity.__dict__, "is_string": True, "conv_bits": 1})
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once()


def test_validate_invalid_float_conversion(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when is_float is True with invalid conversion parameters."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(**{**entity.__dict__, "is_float": True, "conv_bits": 1})
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once()


def test_validate_invalid_register_count(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when register_count is not 2 while is_float is True."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{**entity.__dict__, "is_float": True, "register_count": 1}
    )
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once()


def test_validate_max_change_with_string(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when max_change is set with is_string as True."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{**entity.__dict__, "is_string": True, "max_change": 1.0}
    )
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once()


def test_validate_negative_max_change(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test when max_change is negative."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(**{**entity.__dict__, "max_change": -1.0})
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert not entity.validate()
        mock_warning.assert_called_once()


def test_validate_valid_entity(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Test a valid entity configuration."""
    entity: ModbusEntityDescription = valid_entity_description
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ) as mock_warning:
        assert entity.validate()
        mock_warning.assert_not_called()
