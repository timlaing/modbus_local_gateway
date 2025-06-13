"""Device loader Tests"""

# pylint: disable=unexpected-keyword-arg, protected-access
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.modbus_local_gateway.const import DOMAIN
from custom_components.modbus_local_gateway.entity_management.device_loader import (
    create_device_info,
    get_config_files,
    load_devices,
)
from custom_components.modbus_local_gateway.entity_management.modbus_device_info import (
    ModbusDeviceInfo,
)


def test_get_config_files_only_config_dir(tmp_path: Path, hass: HomeAssistant) -> None:
    """Test getting config files from the main config directory."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file2: Path = config_dir / "dev2.yaml"
    file1.write_text("test1")
    file2.write_text("test2")

    with patch(
        "custom_components.modbus_local_gateway.entity_management.device_loader.CONFIG_DIR",
        str(config_dir),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert "dev2.yaml" in files
        assert files["dev1.yaml"] == str(file1)
        assert files["dev2.yaml"] == str(file2)


def test_get_config_files_with_extra_dir(tmp_path: Path, hass: HomeAssistant) -> None:
    """Test getting config files from both the main config directory and an extra directory."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")
    hass.config.config_dir = str(tmp_path)

    extra_dir: Path = tmp_path / DOMAIN
    extra_dir.mkdir()
    extra_file: Path = extra_dir / "extra.yaml"
    extra_file.write_text("extra")

    with patch(
        "custom_components.modbus_local_gateway.entity_management.device_loader.CONFIG_DIR",
        str(config_dir),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert "extra.yaml" in files
        assert files["extra.yaml"] == str(extra_file)


def test_get_config_files_extra_dir_not_exists(
    tmp_path: Path, hass: HomeAssistant
) -> None:
    """Test getting config files when the extra directory does not exist."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    # Do not create extra_dir
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader.CONFIG_DIR",
            str(config_dir),
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader.DOMAIN",
            "modbus_local_gateway",
        ),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert len(files) == 1


def test_get_config_files_extra_dir_not_a_dir(
    tmp_path: Path, hass: HomeAssistant
) -> None:
    """Test getting config files when the extra directory is not a directory."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    # Create a file with the same name as the domain, not a directory
    extra_file: Path = tmp_path / "modbus_local_gateway"
    extra_file.write_text("not a dir")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader.CONFIG_DIR",
            str(config_dir),
        ),
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader.DOMAIN",
            "modbus_local_gateway",
        ),
    ):
        files: dict[str, str] = get_config_files(hass)
        assert "dev1.yaml" in files
        assert len(files) == 1


def test_get_create_device_info_not_found(hass: HomeAssistant) -> None:
    """Test create_device_info raises FileNotFoundError when file is not found."""
    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={},
        ),
        pytest.raises(FileNotFoundError),
    ):
        create_device_info(hass, "non_existent.yaml")


def test_get_create_device_info_found(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test create_device_info returns ModbusDeviceInfo when file is found."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1)},
        ),
        patch.object(ModbusDeviceInfo, "__init__", return_value=None),
    ):
        device_info: ModbusDeviceInfo = create_device_info(hass, "dev1.yaml")
        assert device_info is not None


async def test_load_devices(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test load_devices loads all devices from config files."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file2: Path = config_dir / "dev2.yaml"
    file1.write_text("test1")
    file2.write_text("test2")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1), "dev2.yaml": str(file2)},
        ),
        patch.object(ModbusDeviceInfo, "__init__", return_value=None),
    ):
        devices: dict[str, ModbusDeviceInfo] = await load_devices(hass)
        assert len(devices) == 2
        assert "dev1.yaml" in devices
        assert "dev2.yaml" in devices


async def test_load_devices_with_error(hass: HomeAssistant, tmp_path: Path) -> None:
    """Test load_devices handles errors when loading device info."""
    config_dir: Path = tmp_path / "device_configs"
    config_dir.mkdir()
    file1: Path = config_dir / "dev1.yaml"
    file1.write_text("test1")

    with (
        patch(
            "custom_components.modbus_local_gateway.entity_management.device_loader"
            ".get_config_files",
            return_value={"dev1.yaml": str(file1)},
        ),
        patch.object(ModbusDeviceInfo, "__init__", side_effect=Exception("Load error")),
    ):
        devices: dict[str, ModbusDeviceInfo] = await load_devices(hass)
        assert len(devices) == 0
        assert "dev1.yaml" not in devices
