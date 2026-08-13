"""Unit tests for the `ModbusEntityDescription` class in the `entity_management.base` module.
These tests cover various scenarios to ensure the validation logic works as expected."""

# pylint: disable=unexpected-keyword-arg, protected-access
from unittest.mock import patch

import pytest

from custom_components.modbus_local_gateway.entity_management.base import (
    ModbusEntityDescription,
)
from custom_components.modbus_local_gateway.entity_management.const import ControlType


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


@pytest.mark.parametrize(
    "control_type", [ControlType.NUMBER, ControlType.SWITCH, ControlType.SELECT]
)
def test_validate_signed_bitfield_rejected_when_writable(
    valid_entity_description: ModbusEntityDescription, control_type: str
) -> None:
    """A writable bit field cannot be signed - the merge assumes unsigned."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{
            **entity.__dict__,
            "conv_bits": 8,
            "is_signed": True,
            "control_type": control_type,
        }
    )
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ):
        assert not entity.validate()


def test_validate_signed_bitfield_allowed_on_sensor(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """Read-only entities keep working: tightening them would delete entities
    from configs that are valid today."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{
            **entity.__dict__,
            "conv_bits": 8,
            "is_signed": True,
            "control_type": ControlType.SENSOR,
        }
    )
    assert entity.validate()


def test_validate_sum_scale_bitfield_rejected_when_writable(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """`sum_scale` has no meaningful inverse, so it cannot be written."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{
            **entity.__dict__,
            "conv_shift_bits": 4,
            "conv_sum_scale": [1.0, 0.1],
            "control_type": ControlType.NUMBER,
        }
    )
    with patch(
        "custom_components.modbus_local_gateway.entity_management.base._LOGGER.warning"
    ):
        assert not entity.validate()


def test_validate_unsigned_bitfield_accepted_when_writable(
    valid_entity_description: ModbusEntityDescription,
) -> None:
    """The ordinary case still validates."""
    entity: ModbusEntityDescription = valid_entity_description
    entity = entity.__class__(
        **{
            **entity.__dict__,
            "conv_bits": 1,
            "conv_shift_bits": 4,
            "control_type": ControlType.SWITCH,
        }
    )
    assert entity.validate()
